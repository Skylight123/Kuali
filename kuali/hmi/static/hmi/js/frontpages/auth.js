(() => {
    'use strict';

    document.querySelectorAll('[data-password-toggle]').forEach((button) => {
        const input = button.parentElement.querySelector('input');
        if (!input) return;
        button.addEventListener('click', () => {
            const visible = input.type === 'text';
            input.type = visible ? 'password' : 'text';
            button.classList.toggle('is-visible', !visible);
            button.setAttribute('aria-label', visible ? 'Tampilkan password' : 'Sembunyikan password');
        });
    });

    const otp = document.querySelector('.otp-input');
    if (otp) {
        otp.addEventListener('input', () => {
            otp.value = otp.value.replace(/\D/g, '').slice(0, 6);
        });
    }
})();
