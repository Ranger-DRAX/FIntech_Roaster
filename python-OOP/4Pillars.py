#Encapsulation
# Prevent direct access to internal data.

class BankAccount:
    def __init__(self):
        self.balance=2000

    def deposit(self,amount):
        if amount >0 :
            self.balance+=amount


    def get_balance(self):
        return self.balance


account = BankAccount()

account.deposit(500)

print(account.get_balance()) # ------->2500/=

"""
2. Inheritance
What problem does it solve?
->Reuse common code.
"""

class User:
    def login(self):
        print("User logged in")


class Customer(User):
    pass


class Merchant(User):
    pass


customer = Customer()
customer.login()

merchant = Merchant()
merchant.login()


"""
Polymorphism
Same method, different behavior
"""
class Payment:
    def pay(self):
        pass


class CardPayment(Payment):
    def pay(self):
        print("Paying by Card")


class MobilePayment(Payment):
    def pay(self):
        print("Paying by Mobile Wallet")


payments = [
    CardPayment(),
    MobilePayment()
]

for p in payments:

    p.pay() 


"""
Abstraction
Hide complexity.
"""
from abc import ABC, abstractmethod

class Notification(ABC):

    @abstractmethod
    def send(self):
        pass


class SMS(Notification):
    def send(self):
        print("SMS Sent")
