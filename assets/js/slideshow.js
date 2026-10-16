// Fullscreen cycling background slideshow for home page.
// Each slide's image is only requested shortly before it is shown, so the
// home page doesn't download every slide up front.
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('slideshow-container');
    if (!container || typeof HOME_SLIDES === 'undefined' || !HOME_SLIDES.length) {
        return;
    }

    const slides = HOME_SLIDES.map((slideData, idx) => {
        const div = document.createElement('div');
        div.className = 'slide-item' + (idx === 0 ? ' active' : '');
        container.appendChild(div);
        return div;
    });

    function load(idx) {
        const div = slides[idx];
        if (div && !div.style.backgroundImage) {
            div.style.backgroundImage = `url("${HOME_SLIDES[idx].webp_url}")`;
        }
    }

    load(0);
    if (slides.length <= 1) return;
    load(1);

    let currentIndex = 0;
    const INTERVAL_MS = 4500;

    setInterval(() => {
        slides[currentIndex].classList.remove('active');
        currentIndex = (currentIndex + 1) % slides.length;
        slides[currentIndex].classList.add('active');
        // Warm up the following slide while this one is on screen
        load((currentIndex + 1) % slides.length);
    }, INTERVAL_MS);
});
