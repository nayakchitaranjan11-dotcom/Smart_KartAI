/**
 * SmartKart AI - Main JavaScript Utilities
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Live Search Suggestions with Debouncing
    const searchInput = document.getElementById('skSearchInput');
    const searchDropdown = document.getElementById('skSearchDropdown');

    if (searchInput && searchDropdown) {
        let debounceTimeout;

        searchInput.addEventListener('input', function () {
            clearTimeout(debounceTimeout);
            const query = this.value.trim();

            if (query.length < 2) {
                searchDropdown.style.display = 'none';
                searchDropdown.innerHTML = '';
                return;
            }

            debounceTimeout = setTimeout(() => {
                fetch(`/products/api/suggestions/?term=${encodeURIComponent(query)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.results && data.results.length > 0) {
                            let html = '<div class="p-2 border-bottom text-muted small fw-semibold">Quick Product Matches</div>';
                            data.results.forEach(item => {
                                html += `
                                    <a href="${item.url}" class="d-flex align-items-center justify-content-between p-2 text-decoration-none text-dark hover-bg-light border-bottom">
                                        <div class="d-flex align-items-center gap-2">
                                            ${item.image ? `<img src="${item.image}" alt="${item.name}" style="width: 32px; height: 32px; object-fit: contain; border-radius: 4px;">` : (item.emoji ? `<span style="font-size: 1.45rem; width: 32px; text-align: center;">${item.emoji}</span>` : '<i class="bi bi-box-seam text-muted fs-5"></i>')}
                                            <div>
                                                <div class="fw-semibold small">${item.name}</div>
                                                <div class="text-muted" style="font-size: 0.75rem;">${item.category} &bull; ${item.unit}</div>
                                            </div>
                                        </div>
                                        <span class="fw-bold text-success small">₹${item.price}</span>
                                    </a>
                                `;
                            });
                            html += `<div class="p-2 text-center"><a href="/products/search/?q=${encodeURIComponent(query)}" class="small text-primary fw-semibold">View all search results &rarr;</a></div>`;
                            searchDropdown.innerHTML = html;
                            searchDropdown.style.display = 'block';
                        } else {
                            searchDropdown.innerHTML = '<div class="p-3 text-center text-muted small">No direct match. Press enter to search full catalogue.</div>';
                            searchDropdown.style.display = 'block';
                        }
                    })
                    .catch(err => console.error('Search error:', err));
            }, 250);
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function (e) {
            if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
                searchDropdown.style.display = 'none';
            }
        });
    }

    // 2. Wishlist Toggle Buttons (AJAX)
    const wishlistBtns = document.querySelectorAll('.sk-wishlist-ajax');
    wishlistBtns.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '';

            fetch('/cart/wishlist/toggle/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: `product_id=${encodeURIComponent(productId)}`
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const icon = this.querySelector('i');
                    if (data.added) {
                        icon.classList.remove('bi-heart');
                        icon.classList.add('bi-heart-fill');
                        this.classList.add('text-danger');
                    } else {
                        icon.classList.remove('bi-heart-fill');
                        icon.classList.add('bi-heart');
                        this.classList.remove('text-danger');
                    }
                    const badge = document.getElementById('navWishlistCount');
                    if (badge) {
                        badge.textContent = data.wishlist_count;
                    }
                }
            })
            .catch(err => console.error('Wishlist error:', err));
        });
    });

    // 3. Recipe Serving Size Dynamic Scaler
    const servingSelect = document.getElementById('recipeServingSelect');
    if (servingSelect) {
        servingSelect.addEventListener('change', function () {
            const servings = this.value;
            const baseServings = parseFloat(this.dataset.baseServings || 4);
            const ratio = parseFloat(servings) / baseServings;

            document.querySelectorAll('.ingredient-qty-val').forEach(el => {
                const baseVal = parseFloat(el.dataset.baseQty);
                if (!isNaN(baseVal)) {
                    el.textContent = (baseVal * ratio).toFixed(2);
                }
            });
        });
    }

    // 4. Copy Coupon Code Helper
    window.copyCouponCode = function (code) {
        navigator.clipboard.writeText(code).then(() => {
            alert(`Coupon code '${code}' copied to clipboard! Paste it at checkout.`);
        });
    };

    // 5. Auto dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alertEl => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });
});


/* ==========================================================================
   ADDED: Blinkit-style instant cart, floating cart bar, toasts & voice search
   ========================================================================== */
(function () {
    'use strict';

    function csrfToken() {
        const el = document.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    // ---- Small toast messages (bottom-centre) ----
    function toast(message, type) {
        const area = document.getElementById('skToastArea');
        if (!area || !message) return;
        const t = document.createElement('div');
        t.className = 'sk-toast ' + (type === 'error' ? 'sk-toast-error' : '');
        t.textContent = message;
        area.appendChild(t);
        setTimeout(() => t.classList.add('show'), 10);
        setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 2600);
    }
    window.skToast = toast;

    // ---- Update navbar badge + floating cart bar from a JSON cart summary ----
    function refreshCartWidgets(data) {
        const count = data.cart_count || 0;
        const navCount = document.getElementById('navCartCount');
        const navTotal = document.getElementById('navCartTotal');
        if (navCount) navCount.textContent = count;
        if (navTotal) {
            navTotal.textContent = '₹' + data.grand_total;
            navTotal.classList.toggle('d-none', count === 0);
        }
        const bar = document.getElementById('skFloatingCart');
        if (bar) {
            bar.classList.toggle('d-none', count === 0);
            const fc = document.getElementById('skFloatCount');
            const ft = document.getElementById('skFloatTotal');
            const fh = document.getElementById('skFloatHint');
            if (fc) fc.textContent = count;
            if (ft) ft.textContent = data.grand_total;
            if (fh) {
                const gap = parseFloat(data.free_delivery_gap || '0');
                fh.textContent = gap > 0 ? `Add ₹${gap.toFixed(0)} more for FREE delivery` : 'Free delivery unlocked 🎉';
            }
            if (count > 0) { bar.classList.remove('sk-bump'); void bar.offsetWidth; bar.classList.add('sk-bump'); }
        }
    }

    // ---- Stepper rendering ----
    function stepperHtml(qty) {
        return `<div class="sk-stepper" role="group" aria-label="Change quantity">
                    <button type="button" class="sk-step-btn" data-step="-1" aria-label="Decrease">−</button>
                    <span class="sk-step-qty">${qty}</span>
                    <button type="button" class="sk-step-btn" data-step="1" aria-label="Increase">+</button>
                </div>`;
    }

    function render(form, qty) {
        form.dataset.qty = qty;
        const btn = form.querySelector('.btn-sk-add');
        let stepper = form.querySelector('.sk-stepper');
        if (qty > 0) {
            if (btn) btn.classList.add('d-none');
            if (!stepper) {
                form.insertAdjacentHTML('beforeend', stepperHtml(qty));
            } else {
                stepper.querySelector('.sk-step-qty').textContent = qty;
            }
        } else {
            if (stepper) stepper.remove();
            if (btn) btn.classList.remove('d-none');
        }
    }

    function setQuantity(form, qty) {
        const productId = form.querySelector('input[name=product_id]').value;
        form.classList.add('sk-busy');
        return fetch('/cart/api/set/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken()
            },
            body: `product_id=${encodeURIComponent(productId)}&quantity=${encodeURIComponent(qty)}`
        })
        .then(res => res.json().then(data => ({ ok: res.ok, data })))
        .then(({ ok, data }) => {
            if (!ok || !data.success) {
                toast(data.message || 'Could not update cart', 'error');
                if (data.substitute_url) window.location = data.substitute_url;
                return;
            }
            // keep every card for the same product in sync (e.g. home page shows it twice)
            document.querySelectorAll(`form.sk-instant-cart[data-product-id="${productId}"]`).forEach(f => render(f, data.quantity));
            refreshCartWidgets(data);
            if (data.message && data.message.startsWith('Only')) toast(data.message, 'error');
        })
        .catch(() => form.submit())   // network problem -> fall back to normal form submit
        .finally(() => form.classList.remove('sk-busy'));
    }

    document.addEventListener('DOMContentLoaded', function () {
        // Enhance every product-card form that has the small green "ADD" button
        const forms = [];
        document.querySelectorAll('form').forEach(form => {
            const btn = form.querySelector('.btn-sk-add');
            const pid = form.querySelector('input[name=product_id]');
            if (!btn || !pid || !form.action.includes('/cart/add/')) return;
            form.classList.add('sk-instant-cart');
            form.dataset.productId = pid.value;
            forms.push(form);

            form.addEventListener('submit', function (e) {
                e.preventDefault();
                setQuantity(form, (parseInt(form.dataset.qty || '0', 10)) + 1);
            });
            form.addEventListener('click', function (e) {
                const step = e.target.closest('.sk-step-btn');
                if (!step) return;
                e.preventDefault();
                const next = Math.max(0, parseInt(form.dataset.qty || '0', 10) + parseInt(step.dataset.step, 10));
                setQuantity(form, next);
            });
        });

        // Show steppers for products that are already in the cart
        if (forms.length) {
            fetch('/cart/api/state/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(r => r.json())
                .then(data => {
                    forms.forEach(f => render(f, data.items[f.dataset.productId] || 0));
                })
                .catch(() => {});
        }

        // ---- Voice search (Web Speech API) ----
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const micBtn = document.getElementById('skVoiceSearchBtn');
        const searchInput = document.getElementById('skSearchInput');
        if (SpeechRecognition && micBtn && searchInput) {
            micBtn.classList.remove('d-none');
            const recognizer = new SpeechRecognition();
            recognizer.lang = 'en-IN';
            recognizer.interimResults = false;
            recognizer.maxAlternatives = 1;
            micBtn.addEventListener('click', function () {
                try { recognizer.start(); } catch (err) { /* already listening */ }
                micBtn.classList.add('listening');
                toast('Listening… say a product name, e.g. "paneer"');
            });
            recognizer.addEventListener('result', function (event) {
                const spoken = event.results[0][0].transcript.replace(/[.?!]$/, '');
                searchInput.value = spoken;
                searchInput.form.submit();
            });
            recognizer.addEventListener('end', () => micBtn.classList.remove('listening'));
            recognizer.addEventListener('error', () => { micBtn.classList.remove('listening'); toast('Voice search unavailable — please type instead', 'error'); });
        }
    });
})();
