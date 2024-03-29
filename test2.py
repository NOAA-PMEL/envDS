import datetime
from typing import Optional

from pydantic import EmailStr

from redis_om import JsonModel, Field, Migrator


class Customer(JsonModel):
    first_name: str
    last_name: str = Field(index=True)
    email: EmailStr
    join_date: datetime.date
    age: int = Field(index=True)
    bio: Optional[str]


# First, we create a new `Customer` object:
andrew = Customer(
    first_name="Andrew",
    last_name="Brookins",
    email="andrew.brookins@example.com",
    join_date=datetime.date.today(),
    age=38,
    bio="Python developer, works at Redis, Inc."
)

# The model generates a globally unique primary key automatically
# without needing to talk to Redis.
# print(andrew.pk)
# > "01FJM6PH661HCNNRC884H6K30C"

# # We can save the model to Redis by calling `save()`:
andrew.save()

# # Expire the model after 2 mins (120 seconds)
# andrew.expire(120)

# To retrieve this customer with its primary key, we use `Customer.get()`:
# assert Customer.get(andrew.pk) == andrew

Migrator().run()

# Find all customers with the last name "Brookins"
Customer.find(Customer.last_name == "Brookins").all()

# Find all customers that do NOT have the last name "Brookins"
Customer.find(Customer.last_name != "Brookins").all()

# Find all customers whose last name is "Brookins" OR whose age is 
# 100 AND whose last name is "Smith"
results = Customer.find((Customer.last_name == "Brookins") | (
        Customer.age == 100
) & (Customer.last_name == "Smith")).all()

print(results)