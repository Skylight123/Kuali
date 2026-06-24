(() => {
    'use strict';

    document.querySelectorAll('[data-password-toggle]').forEach((button) => {
        const input = button.parentElement.querySelector('input');
        if (!input) return;

        button.addEventListener('click', () => {
            const visible = input.type === 'text';
            input.type = visible ? 'password' : 'text';
            button.classList.toggle('is-visible', !visible);
            button.setAttribute('aria-label', visible ? 'Tampilkan sandi' : 'Sembunyikan sandi');
        });
    });

    const otp = document.querySelector('.otp-input');
    if (otp) {
        otp.addEventListener('input', () => {
            otp.value = otp.value.replace(/\D/g, '').slice(0, 6);
        });
    }

    document.querySelectorAll('[data-auth-form]').forEach((form) => {
        const button = form.querySelector('[data-submit-button]');
        if (!button) return;

        form.addEventListener('submit', () => {
            button.disabled = true;
            button.innerHTML = `<span class="spinner"></span> ${button.dataset.loadingText || 'Memproses...'}`;
        });
    });
})();
