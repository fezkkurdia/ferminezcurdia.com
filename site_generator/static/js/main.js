// Mobile navigation menu toggle
document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menu-toggle');
    const siteNav = document.getElementById('site-nav');

    if (menuToggle && siteNav) {
        menuToggle.addEventListener('click', () => {
            const isOpen = siteNav.classList.toggle('open');
            menuToggle.setAttribute('aria-expanded', isOpen);
        });
    }
});
