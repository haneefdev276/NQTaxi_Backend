from django.urls import path
from .views import FareListView, calculate_fare, fare_detail

urlpatterns = [  #To Check the every rule in urlpatterns
    path('',FareListView.as_view()),  #'' = Empty, FareListView(Class) == as view(funtion)
    
    path('calculate/', calculate_fare),
      path('<str:type>/',fare_detail),
      
          #'' = Empty, FareListView(Class) == as view(funtion) 
                                                           
]