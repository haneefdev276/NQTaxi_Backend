"""
Trip State Machine for NQTaxi.

This module centralizes ALL transition logic, validation rules, and side-effects
for the Trip lifecycle. Views become thin — they just call `TripStateMachine.trigger()`
and return the result.

State Diagram:
─────────────────────────────────────────────────────────────────────────────
                          ┌─────────────┐
                          │  REQUESTED  │◄─── rider creates trip
                          └──────┬──────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │ driver.accept()  │                  │ driver.reject() [no state change]
              ▼                  │ rider/driver      │
        ┌──────────┐             │  .cancel()        │
        │ ACCEPTED │             ▼                  │
        └────┬─────┘       ┌───────────┐            │
             │             │ CANCELLED │◄───────────┘
             │ driver.start() (OTP)    │
             ▼             │           │
        ┌──────────┐       │  cancel   │
        │  ONGOING │───────┘           │
        └────┬─────┘                   │
             │ driver.complete()        │
             ▼                         │
        ┌───────────┐                  │
        │ COMPLETED │                  │
        └───────────┘                  │
─────────────────────────────────────────────────────────────────────────────

Usage:
    from apps.trips.state_machine import TripStateMachine, TripTransitionError

    sm = TripStateMachine(trip)
    sm.accept(by_user=request.user)
    sm.start(by_user=request.user, otp='123456')
    sm.complete(by_user=request.user, fare=Decimal('180.00'), distance_km=Decimal('7.5'))
    sm.cancel(by_user=request.user, reason='Driver is late')
    sm.reject(by_user=request.user)
"""

import random
from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction

from apps.drivers.models import (
    DriverProfile,
    Wallet,
    Transaction,
    TransactionType,
)


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TripTransitionError(Exception):
    """
    Raised when a state transition is invalid.

    Attributes:
        message  -- human-readable description
        code     -- HTTP-style status code hint (409 = conflict, 403 = forbidden, 400 = bad request)
    """
    def __init__(self, message: str, code: int = 409):
        super().__init__(message)
        self.message = message
        self.code = code


# ─────────────────────────────────────────────────────────────────────────────
# Transition table
# ─────────────────────────────────────────────────────────────────────────────

# Maps action_name → allowed_from_states
# None as 'to' state means the trip status does NOT change (e.g. reject)
TRANSITION_TABLE = {
    'accept':   {'from': ('REQUESTED',),                             'to': 'ACCEPTED'},
    'reject':   {'from': ('REQUESTED',),                             'to': None},          # no status change
    'start':    {'from': ('ACCEPTED',),                              'to': 'ONGOING'},
    'complete': {'from': ('ONGOING',),                               'to': 'COMPLETED'},
    'cancel':   {'from': ('REQUESTED', 'ACCEPTED', 'ONGOING'),       'to': 'CANCELLED'},
}


# ─────────────────────────────────────────────────────────────────────────────
# State Machine
# ─────────────────────────────────────────────────────────────────────────────

class TripStateMachine:
    """
    Encapsulates the entire Trip lifecycle.

    Each public method corresponds to one allowed action. Methods:
    - validate the current state
    - validate who is performing the action
    - apply the state change atomically
    - run all side-effects (stats counters, wallet credit, etc.)
    - return the refreshed Trip instance

    The `reject` action is special: the trip stays REQUESTED so another
    driver can pick it up, only the driver's rejected_rides counter is bumped.
    """

    def __init__(self, trip):
        self.trip = trip

    # ─────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────

    def _assert_state(self, action: str):
        """Raise TripTransitionError if the current trip state is not in allowed_from."""
        allowed = TRANSITION_TABLE[action]['from']
        if self.trip.status not in allowed:
            raise TripTransitionError(
                f"Cannot '{action}' a trip that is currently '{self.trip.status}'. "
                f"Allowed states for this action: {', '.join(allowed)}."
            )

    def _assert_assigned_driver(self, user, action: str):
        """Raise TripTransitionError if user is not the assigned driver on this trip."""
        if self.trip.driver != user:
            raise TripTransitionError(
                f"Only the assigned driver can '{action}' this trip.",
                code=403,
            )

    def _get_driver_profile(self, user) -> DriverProfile:
        """Return the DriverProfile for user or raise TripTransitionError."""
        try:
            return user.driver_profile
        except Exception:
            raise TripTransitionError(
                "A driver profile is required to perform this action.",
                code=403,
            )

    @staticmethod
    def _credit_wallet(driver_profile: DriverProfile, trip):
        """
        Credit driver wallet with the trip fare.
        Creates a Transaction record and updates Wallet totals.
        No-op if fare is zero or None.
        """
        fare = trip.fare or Decimal('0.00')
        if fare <= 0:
            return

        wallet, _ = Wallet.objects.get_or_create(driver=driver_profile)
        wallet.balance      = Decimal(str(wallet.balance)) + fare
        wallet.total_earned = Decimal(str(wallet.total_earned)) + fare
        wallet.save(update_fields=['balance', 'total_earned', 'updated_at'])

        Transaction.objects.create(
            wallet=wallet,
            txn_type=TransactionType.CREDIT,
            amount=fare,
            description=f'Trip fare — {trip.pickup_address} → {trip.drop_address}',
            reference=str(trip.pk),
            balance_after=wallet.balance,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Public transition methods
    # ─────────────────────────────────────────────────────────────────────

    @db_transaction.atomic
    def accept(self, by_user) -> 'Trip':
        """
        REQUESTED → ACCEPTED

        Who:    Any verified driver.
        Effect: Links driver to trip, increments driver.accepted_rides.
        """
        self._assert_state('accept')
        driver_profile = self._get_driver_profile(by_user)

        now = timezone.now()
        self.trip.driver      = by_user
        self.trip.status      = 'ACCEPTED'
        self.trip.accepted_at = now
        self.trip.save(update_fields=['driver', 'status', 'accepted_at', 'updated_at'])

        # Side-effect: driver stats
        driver_profile.accepted_rides += 1
        driver_profile.save(update_fields=['accepted_rides', 'updated_at'])

        return self.trip

    @db_transaction.atomic
    def reject(self, by_user) -> dict:
        """
        REQUESTED → REQUESTED  (status unchanged)

        Who:    Any driver.
        Effect: Increments driver.rejected_rides. Trip stays available.
        Returns a dict (no trip update), not a Trip object.
        """
        self._assert_state('reject')
        driver_profile = self._get_driver_profile(by_user)

        # Side-effect: driver stats only — trip status does NOT change
        driver_profile.rejected_rides += 1
        driver_profile.save(update_fields=['rejected_rides', 'updated_at'])

        return {'detail': 'Trip rejected. It remains available for other drivers.'}

    @db_transaction.atomic
    def start(self, by_user, otp: str) -> 'Trip':
        """
        ACCEPTED → ONGOING

        Who:    The assigned driver only.
        Guards: OTP must match the one given to the rider at booking time.
        Effect: Clears OTP, sets started_at.
        """
        self._assert_state('start')
        self._assert_assigned_driver(by_user, 'start')

        if not otp or otp != self.trip.otp:
            raise TripTransitionError(
                "Invalid OTP. Ask the rider for the 6-digit code shown on their screen.",
                code=400,
            )

        now = timezone.now()
        self.trip.status     = 'ONGOING'
        self.trip.started_at = now
        self.trip.otp        = ''   # invalidate OTP after use
        self.trip.save(update_fields=['status', 'started_at', 'otp', 'updated_at'])

        return self.trip

    @db_transaction.atomic
    def complete(
        self,
        by_user,
        fare: Decimal | None = None,
        distance_km: Decimal | None = None,
    ) -> 'Trip':
        """
        ONGOING → COMPLETED

        Who:    The assigned driver only.
        Effect:
          - Sets fare / distance_km if provided
          - Credits driver wallet with fare
          - Increments driver.total_rides
          - Increments rider.total_rides (best-effort)
        """
        self._assert_state('complete')
        self._assert_assigned_driver(by_user, 'complete')
        driver_profile = self._get_driver_profile(by_user)

        now = timezone.now()
        self.trip.status       = 'COMPLETED'
        self.trip.completed_at = now

        if fare is not None:
            self.trip.fare = fare
        if distance_km is not None:
            self.trip.distance_km = distance_km

        self.trip.save(update_fields=[
            'status', 'completed_at', 'fare', 'distance_km', 'updated_at',
        ])

        # Side-effect: driver stats
        driver_profile.total_rides += 1
        driver_profile.save(update_fields=['total_rides', 'updated_at'])

        # Side-effect: wallet credit
        self._credit_wallet(driver_profile, self.trip)

        # Side-effect: rider stats (best-effort — profile may not exist)
        try:
            rider_profile = self.trip.rider.rider_profile
            rider_profile.total_rides += 1
            rider_profile.save(update_fields=['total_rides'])
        except Exception:
            pass

        return self.trip

    @db_transaction.atomic
    def cancel(self, by_user, reason: str = '') -> 'Trip':
        """
        REQUESTED | ACCEPTED | ONGOING → CANCELLED

        Who:    The rider OR the assigned driver.
        Effect: Sets cancelled_by, cancellation_reason, cancelled_at.
        """
        self._assert_state('cancel')

        is_rider  = (self.trip.rider == by_user)
        is_driver = (self.trip.driver == by_user)

        if not is_rider and not is_driver:
            raise TripTransitionError(
                "You are not authorised to cancel this trip.",
                code=403,
            )

        now = timezone.now()
        self.trip.status              = 'CANCELLED'
        self.trip.cancelled_at        = now
        self.trip.cancelled_by        = 'RIDER' if is_rider else 'DRIVER'
        self.trip.cancellation_reason = reason
        self.trip.save(update_fields=[
            'status', 'cancelled_at', 'cancelled_by', 'cancellation_reason', 'updated_at',
        ])

        return self.trip

    # ─────────────────────────────────────────────────────────────────────
    # Class-level factory
    # ─────────────────────────────────────────────────────────────────────

    @classmethod
    def for_trip(cls, trip) -> 'TripStateMachine':
        """Convenience factory: TripStateMachine.for_trip(trip).accept(user)"""
        return cls(trip)

    # ─────────────────────────────────────────────────────────────────────
    # Utility: can this action be performed right now?
    # ─────────────────────────────────────────────────────────────────────

    def can(self, action: str) -> bool:
        """Return True if `action` is valid given the current trip state."""
        rule = TRANSITION_TABLE.get(action)
        if rule is None:
            return False
        return self.trip.status in rule['from']

    def available_actions(self) -> list[str]:
        """Return all actions currently valid for this trip's state."""
        return [action for action in TRANSITION_TABLE if self.can(action)]

    def __repr__(self):
        return (
            f'<TripStateMachine trip={self.trip.pk} '
            f'status={self.trip.status} '
            f'available={self.available_actions()}>'
        )
