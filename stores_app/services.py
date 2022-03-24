import os
from decimal import Decimal
from typing import Dict

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_delete

from config.settings import MEDIA_ROOT
from discounts_app.models import Discount
from orders_app.models import Order
from settings_app.config_project import SUCCESS_DEL_STORE, SUCCESS_DEL_PRODUCT
from stores_app.models import Seller, SellerProduct
from goods_app.models import Product, ProductCategory


User = get_user_model()


class StoreServiceMixin:
    """
    Mixin with functions for queries by project models Seller and SellerProduct

    All available methods:
    get_store(slug) - get Seller instance with slug=slug
    get_user_stores(user) - get all Seller models by owner=user
    remove_store(request) - remove Seller instance with id=request.id=request
    create_seller_product(data) - create SelleProduct instance
    edit_seller_product(data, instance) - edit SellerProduct instance
    get_products(query params) - get products
 ?? get_categories() - get all categories
 ?? get_discounts() - get all discounts
 ?? get_price_with_discount(price, discount) - Get the price with discount, if it had
    get_seller_products(user) - get SellerProducts query by Sellers owner=user
    remove_seller_product(request) - Remove SellerProduct instance with id=request.id
    remove_old_file(file) - Method for remove file on path=MEDIA_ROOT + file
    """

    @classmethod
    def get_store(cls, slug: str) -> QuerySet:
        """
        Get store with slug
        """
        return Seller.objects.select_related('owner').get(slug=slug)

    @classmethod
    def get_user_stores(cls, user: User) -> QuerySet:
        """
        Get all stores by user
        """
        return Seller.objects.filter(owner=user)

    @classmethod
    def remove_store(cls, request) -> None:
        """
        Remove store
        """
        store = Seller.objects.get(id=request.GET.get('id'))
        messages.add_message(request, SUCCESS_DEL_STORE,
                             _(f'The {store.name} was removed'))
        store.delete()

    def create_seller_product(self, data: Dict) -> bool:
        """
        Create new SellerProduct
        """
        if SellerProduct.objects.filter(seller=data['seller'], product=data['product']).exists():
            return False
        else:
            price_after_discount = self.get_price_with_discount(data['price'], data['discount'])
            SellerProduct.objects.create(
                seller=data['seller'],
                product=data['product'],
                discount=data['discount'],
                price=data['price'],
                price_after_discount=price_after_discount,
                quantity=data['quantity'])
            return True

    def edit_seller_product(self, data: Dict, instance: SellerProduct) -> None:
        """
        Edit SellerProduct instance
        """
        price_after_discount = self.get_price_with_discount(data['price'], data['discount'])
        instance.discount = data['discount']
        instance.price = data['price']
        instance.price_after_discount = price_after_discount
        instance.quantity = data['quantity']
        instance.save()

    @classmethod
    def get_price_with_discount(cls, price: Decimal, discount: Discount) -> Decimal:
        """
        Get the price with discount, if it had
        """
        if discount.percent:
            return price * Decimal(1 - discount.percent / 100)
        elif discount.amount:
            return price - Decimal(discount.amount)
        else:
            return price

    @classmethod
    def get_seller_products(cls, user: User) -> QuerySet:
        """
        Get all products, added by user
        """
        return SellerProduct.objects.select_related('seller', 'discount', 'product')\
                                    .filter(seller__owner=user)

    @classmethod
    def remove_seller_product(cls, request) -> None:
        """
        Remove store
        """
        item = SellerProduct.objects.select_related('seller', 'product').get(id=request.GET.get('id'))
        messages.add_message(request, SUCCESS_DEL_PRODUCT,
                             _(f'Product {item.product.name} from the store {item.seller.name} was removed'))
        item.delete()

    @classmethod
    def get_categories(cls) -> QuerySet:
        """
        Get all categories
        """
        return ProductCategory.objects.all()

    @classmethod
    def get_products(cls, **kwargs) -> QuerySet:
        if 'category_id' in kwargs.keys():
            return Product.objects.select_related('category').filter(category=kwargs.get('category_id'))
        elif 'instance' in kwargs.keys():
            return Product.objects.select_related('category').filter(seller_products__seller=kwargs.get('instance'))
        else:
            return Product.objects.select_related('category').all()

    @classmethod
    def get_discounts(cls) -> QuerySet:
        return Discount.objects.all()

    @classmethod
    def get_last_order(cls, user: User) -> QuerySet:
        return Order.objects.filter(customer=user).last()

    @classmethod
    def get_all_orders(cls, user) -> QuerySet:
        return Order.objects.filter(customer=user)

    @classmethod
    def remove_old_file(cls, file: str) -> None:
        """
        Method for remove old file, when update the store-logo for example
        """
        path = os.path.normpath(os.path.join(MEDIA_ROOT, str(file)))
        if os.path.exists(path):
            os.remove(path)

    def request_add_new_product(self, product, user):
        product.is_published = False
        product.user = user
        product.save()


@receiver(post_delete, sender=Seller)
def delete_IconFile(**kwargs) -> None:
    """
    The signal for removing icon Seller, when the store is deleting
    """
    file = kwargs.get('instance')
    file.icon.delete(save=False)
