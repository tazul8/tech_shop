from django.conf import settings 
from django import forms
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import request, JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, TemplateView
from django.utils import timezone
from .forms import CheckoutForm, CouponForm, RefundForm
from .models import Banner, Item, OrderItem, Order, Address, Payment, Coupon, Refund
import random
import string
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


class SuccessView(TemplateView):
    template_name = 'success.html'


class CancelView(TemplateView):
    template_name = 'cancel.html'


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'order': order  
            }
            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("store:checkout") 
    
    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                apartment_address = form.cleaned_data.get('apartment_address')
                country = form.cleaned_data.get('country')
                state = form.cleaned_data.get('state')
                zip = form.cleaned_data.get('zip')
                payment_option = form.cleaned_data.get('payment_option')
                address = Address(
                    user=self.request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    state=state,
                    zip=zip,
                    )
                address.save()
                order.address = address
                order.save()

                if payment_option == 'S':
                    return redirect('store:stripe-page')
                elif payment_option == 'P':
                    return redirect('store:paypal-page')
                else:
                    messages.warning(self.request, "Invalid payment option selected")
                    return redirect("store:checkout")
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("store:order-summary")


class StripePage(TemplateView):
    template_name = 'stripe_page.html'


class StripePaymentView(View):
    def post(self, request, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        YOUR_DOMAIN = "http://127.0.0.1:8000"
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {   
                        'name': 'Shopping',
                        'quantity': 1,
                        'currency': 'usd',
                        'amount': 100,
                        'amount': int(order.get_total() * 100),        # cents
                    },
                ],
                mode='payment',
                success_url=YOUR_DOMAIN + '/success/',
                cancel_url=YOUR_DOMAIN + '/cancel/',
            )
            # create the payment
            payment = Payment()
            payment.stripe_charge_id = checkout_session['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()
            # assign the payment to the order
            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            order.ordered = True
            order.payment = payment
            order.ref_code = create_ref_code()
            order.save()
        except Exception as e:
            return str(e)

        return redirect(checkout_session.url, code=303)


class PaypalPage(TemplateView):
    template_name = 'paypal_page.html'


class HomeView(ListView):
    model = Item
    template_name = "index.html"

    def get_context_data(self, *args, **kwargs):
        banners = Banner.objects.all()[:3]
        context = super(HomeView, self).get_context_data(*args, **kwargs)

        items = Item.objects.filter(featured=True).order_by('-id')
        context["banners"] = banners
        context["items"] = items
        return context


class ItemListView(ListView):
    model = Item 
    paginate_by = 12
    template_name = "item_list.html"

    def get_context_data(self, *args, **kwargs):
        items = Item.objects.filter(category=self.kwargs['slug']).order_by('-id')
        context = super(ItemListView, self).get_context_data(*args, **kwargs)
        context["object_list"] = items
        return context


class OrderSummaryView(LoginRequiredMixin, View): 
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            couponform = CouponForm()
            context = {
                'object': order,
                'couponform': couponform,
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")
        

class ItemDetailView(DetailView):
    model = Item
    template_name = "item_detail.html"


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(item=item, user=request.user, ordered=False)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("store:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
    return redirect("store:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(item=item, user=request.user, ordered=False)[0]
            order.items.remove(order_item)
            messages.info(request, "This item was removed from your cart.")
            return redirect("store:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("store:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("store:product", slug=slug)
    

@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(item=item, user=request.user, ordered=False)[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated")
            return redirect("store:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("store:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("store:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist.")
        return redirect("store:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("store:order-summary") 
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("store:order-summary") 
    

class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form 
        }
        return render(self.request, 'request_refund.html', context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            try:
                # edit the order
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()
                # store the refund
                refund = Refund()
                refund.order = order 
                refund.reason = message
                refund.email = email 
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("store:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("store:request-refund")



