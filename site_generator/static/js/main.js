// Mobile navigation menu toggle, Masonry Layout, Back-to-Top Button & Speculative Preloader
document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Menu Toggle
    const menuToggle = document.getElementById('menu-toggle');
    const siteNav = document.getElementById('site-nav');

    if (menuToggle && siteNav) {
        menuToggle.addEventListener('click', () => {
            const isOpen = siteNav.classList.toggle('open');
            menuToggle.setAttribute('aria-expanded', isOpen);
        });
    }

    // 2. Back to top button
    const backToTop = document.getElementById('back-to-top');
    if (backToTop) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 450) {
                backToTop.classList.add('visible');
            } else {
                backToTop.classList.remove('visible');
            }
        }, { passive: true });

        backToTop.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // 3. Masonry Gallery Layout Engine
    initMasonry();

    // 4. Speculative Preloader on Thumbnail Hover/Touch
    initSpeculativePreloader();
});

function initSpeculativePreloader() {
    const gallery = document.getElementById('photo-gallery');
    if (!gallery) return;

    const preloadedUrls = new Set();
    function preloadUrl(url) {
        if (!url || preloadedUrls.has(url)) return;
        preloadedUrls.add(url);
        const img = new Image();
        img.src = url;
    }

    let hoverTimer = null;

    // Hover intent (60ms): triggers when user pauses pointer over a photo thumbnail
    gallery.addEventListener('pointerover', (e) => {
        const link = e.target.closest('a[data-pswp-width]');
        if (!link || !link.href) return;
        clearTimeout(hoverTimer);
        hoverTimer = setTimeout(() => {
            preloadUrl(link.href);
        }, 60);
    }, { passive: true });

    gallery.addEventListener('pointerout', () => {
        clearTimeout(hoverTimer);
    }, { passive: true });

    // Touchstart: instantly preload on touch before tap-click completes
    gallery.addEventListener('touchstart', (e) => {
        const link = e.target.closest('a[data-pswp-width]');
        if (link && link.href) {
            preloadUrl(link.href);
        }
    }, { passive: true });
}

function initMasonry() {
    const gallery = document.getElementById('photo-gallery');
    if (!gallery || !gallery.classList.contains('masonry-grid')) return;

    const items = Array.from(gallery.querySelectorAll('.gallery-item'));
    if (!items.length) return;

    function layout() {
        const containerWidth = gallery.clientWidth;
        if (!containerWidth) return;

        // Determine column count dynamically to fill the entire screen width
        // Target column width is ~330px for high-definition photo viewing
        let cols = Math.max(1, Math.round(containerWidth / 330));
        if (containerWidth < 550) {
            cols = 1;
        }

        const gap = containerWidth < 600 ? 8 : 12;
        const totalGaps = (cols - 1) * gap;
        const colWidth = (containerWidth - totalGaps) / cols;
        const colHeights = new Array(cols).fill(0);

        items.forEach(item => {
            // Find column with the lowest current height
            let minCol = 0;
            for (let c = 1; c < cols; c++) {
                if (colHeights[c] < colHeights[minCol]) {
                    minCol = c;
                }
            }

            const x = Math.round(minCol * (colWidth + gap));
            const y = Math.round(colHeights[minCol]);

            // Calculate height using the precomputed aspect ratio
            const arStr = item.style.getPropertyValue('--aspect-ratio');
            const ar = parseFloat(arStr) || 1.5;
            const itemHeight = Math.round(colWidth / ar);

            item.style.width = `${Math.round(colWidth)}px`;
            item.style.height = `${itemHeight}px`;
            item.style.transform = `translate3d(${x}px, ${y}px, 0)`;
            item.classList.add('laid-out');

            colHeights[minCol] += itemHeight + gap;
        });

        const maxHeight = Math.max(...colHeights);
        gallery.style.height = `${maxHeight}px`;
    }

    // Run layout immediately
    layout();

    // Re-run on window resize with debounce
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(layout, 50);
    });

    // Also run after all images have fully loaded in case of late font render
    window.addEventListener('load', layout);
}
