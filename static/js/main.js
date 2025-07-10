import { updateDateTime } from './utils.js';
import { startDataFetching } from './dataFetch.js';
import { updateDetectionData } from './dataDetection.js';

document.addEventListener('DOMContentLoaded', () => {
    // Update time and date every second
    setInterval(updateDateTime, 1000);
    updateDateTime();

    // Cache last valid stem outline
    let lastValidSrc = null;

    // Update stem outline every 200ms
    setInterval(() => {
        const stemOutline = document.querySelector('.stem-outline');
        stemOutline.classList.add('loading');
        const img = stemOutline.querySelector('img');
        img.onload = () => {
            stemOutline.classList.remove('loading');
            if (img.src.includes('No Stem Outline')) {
                console.warn('Kinect error: No stem outline');
                // Revert to last valid image if available
                if (lastValidSrc) {
                    img.src = lastValidSrc;
                }
            } else {
                lastValidSrc = img.src; // Cache valid image
            }
        };
        img.onerror = () => {
            stemOutline.classList.remove('loading');
            console.error('Failed to load stem outline');
            if (lastValidSrc) {
                img.src = lastValidSrc;
            }
        };
        img.src = `/get_stem_outline?t=${Date.now()}`;
    }, 200);

    // Start periodic data fetching
    startDataFetching();

    // Ensure detection data (including height) updates
    setInterval(updateDetectionData, 5000);
    updateDetectionData();
});