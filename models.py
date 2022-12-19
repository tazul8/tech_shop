from django.conf import settings 
from django.db import models
from django.shortcuts import reverse
from django_countries.fields import CountryField
import stripe


CATEGORY_CHOICES = (
    ('laptop', 'laptop'),
    ('monitor', 'monitor'),
    ('tablet', 'tablet'),
    ('camera', 'camera')
)


class Banner(models.Model):
    alternative_text = models.CharField(max_length=255)
    image = models.ImageField()

    def __str__(self):
        return self.alternative_text


class Item(models.Model):
    title = models.CharField(max_length=500)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=7)
    slug = models.SlugField()
    image = models.ImageField()
    alternative_text = models.CharField(max_length=255)
    snippet = models.TextField()
    description = models.TextField()
    featured = models.BooleanField(default=False)
    spec_name1 = models.CharField(max_length=255)
    spec_value1 = models.TextField()
    spec_name2 = models.CharField(max_length=255)
    spec_value2 = models.TextField()
    spec_name3 = models.CharField(max_length=255)
    spec_value3 = models.TextField()
    spec_name4 = models.CharField(max_length=255)
    spec_value4 = models.TextField()
    spec_name5 = models.CharField(max_length=255)
    spec_value5 = models.TextField()
    spec_name6 = models.CharField(max_length=255, blank=True, null=True)
    spec_value6 = models.TextField(blank=True, null=True)
    spec_name7 = models.CharField(max_length=255, blank=True, null=True)
    spec_value7 = models.TextField(blank=True, null=True)
    spec_name8 = models.CharField(max_length=255, blank=True, null=True)
    spec_value8 = models.TextField(blank=True, null=True)
    spec_name9 = models.CharField(max_length=255, blank=True, null=True)
    spec_value9 = models.TextField(blank=True, null=True)
    spec_name10 = models.CharField(max_length=255, blank=True, null=True)
    spec_value10 = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("store:product", kwargs={'slug': self.slug})

    def get_add_to_cart_url(self):
        return reverse("store:add-to-cart", kwargs={'slug': self.slug})

    def get_remove_from_cart_url(self):
        return reverse("store:remove-from-cart", kwargs={'slug': self.slug})


class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.item.title}"

    def get_total_item_price(self):
        return self.quantity * self.item.price

    def get_total_discount_item_price(self):
        return self.quantity * self.item.discount_price

    def get_amount_saved(self):
        return self.get_total_item_price() - self.get_total_discount_item_price()

    def get_final_price(self):
        if self.item.discount_price:
            return self.get_total_discount_item_price()
        return self.get_total_item_price()


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ref_code = models.CharField(max_length=20)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField()
    ordered = models.BooleanField(default=False)
    address = models.ForeignKey('Address', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, blank=True, null=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, blank=True, null=True)
    being_delivered = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    refund_requested = models.BooleanField(default=False)
    refund_granted = models.BooleanField(default=False)
    
    def __str__(self):
        return self.user.username 

    def get_sub_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        return total 

    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        if self.coupon:
            total -= self.coupon.amount 
        return total


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username  

    class Meta:
        verbose_name_plural = 'Addresses'


class Payment(models.Model):
    stripe_charge_id = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username 


class Coupon(models.Model):
    code = models.CharField(max_length=15)
    amount = models.FloatField()

    def __str__(self):
        return self.code 


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    accepted = models.BooleanField(default=False)
    email = models.EmailField()

    def __str__(self):
        return f"{self.pk}"


