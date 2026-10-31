from apps.cart.models import Cart, CartItem


def get_or_create_cart(request):
    """
    Retrieves or creates the appropriate Cart instance for the request.
    If the user is authenticated, uses the user-bound cart.
    Otherwise, uses the session-bound cart.
    """
    if not hasattr(request, 'session'):
        return None

    if request.user.is_authenticated:
        # Check if user already has an active cart
        cart, created = Cart.objects.get_or_create(user=request.user)

        # If user had a session cart before logging in, merge items
        if request.session.session_key:
            session_cart = Cart.objects.filter(session_key=request.session.session_key, user__isnull=True).first()
            if session_cart and session_cart != cart:
                for session_item in session_cart.items.all():
                    existing_item, item_created = CartItem.objects.get_or_create(
                        cart=cart,
                        product=session_item.product,
                        defaults={'quantity': session_item.quantity}
                    )
                    if not item_created:
                        # Cap at product stock
                        new_qty = min(existing_item.quantity + session_item.quantity, session_item.product.stock_quantity)
                        existing_item.quantity = new_qty
                        existing_item.save()
                # Copy coupon if user cart didn't have one
                if session_cart.coupon and not cart.coupon:
                    cart.coupon = session_cart.coupon
                    cart.save()
                session_cart.delete()
        return cart
    else:
        # Anonymous user
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, user__isnull=True)
        return cart
