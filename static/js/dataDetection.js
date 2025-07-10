import { endpoints } from './routing.js';

// Function to fetch an image of the detected species
export async function fetchSpeciesImage(speciesName) {
    try {
        const response = await fetch(`https://en.wikipedia.org/w/api.php?action=query&titles=${encodeURIComponent(speciesName)}&prop=pageimages&format=json&pithumbsize=100&origin=*`);
        const data = await response.json();
        const pages = data.query.pages;
        const pageId = Object.keys(pages)[0];
        const imageUrl = pages[pageId].thumbnail?.source;
        return imageUrl || "https://via.placeholder.com/50";
    } catch (error) {
        console.error("Error fetching species image:", error);
        return "https://via.placeholder.com/50";
    }
}

// Fetch and display detection insights
export async function updateDetectionData() {
    try {
        // Fetch detection data
        const detectionResponse = await fetch(endpoints.inferenceData);
        if (!detectionResponse.ok) throw new Error(`HTTP error! Status: ${detectionResponse.status}`);
        const detectionData = await detectionResponse.json();

        // Fetch plant height
        const heightResponse = await fetch('/plant_height');
        let heightData = { height: 0, plant_name: "Unknown", timestamp: "N/A" };
        if (heightResponse.ok) {
            heightData = await heightResponse.json();
        } else {
            console.warn("Failed to fetch plant height");
        }

        // Find the highest confidence detection
        const highestConfidenceDetection = detectionData.reduce((prev, current) =>
            prev.confidence > current.confidence ? prev : current,
            { confidence: 0, label: "No Detection", category: "motion" }
        );

        // Highlight the detection insights box if confidence > 230
        const detectionInsightsBox = document.getElementById("detection-insights-box");
        if (highestConfidenceDetection.confidence > 230) {
            detectionInsightsBox.classList.add("highlight");
        } else {
            detectionInsightsBox.classList.remove("highlight");
        }

        // Fetch an image of the detected species
        const imageUrl = await fetchSpeciesImage(highestConfidenceDetection.label);

        // Create the insight card
        const insightCard = `
            <div class="insight-card">
                <img src="${imageUrl}" alt="${highestConfidenceDetection.label}" style="width: 50px; height: 50px;">
                <div class="content">
                    <h6>Update: ${highestConfidenceDetection.label} detected with ${highestConfidenceDetection.confidence.toFixed(2)} confidence!</h6>
                    <p>Category: ${highestConfidenceDetection.category}</p>
                    <p>Plant: ${heightData.plant_name}, Height: ${heightData.height.toFixed(1)} cm</p>
                    <p>Measured: ${heightData.timestamp}</p>
                </div>
            </div>
        `;

        // Update the Detection Insights section
        const detectionInsights = document.getElementById("detection-insights");
        detectionInsights.innerHTML = insightCard;

        // Update the Last 5 Detections table
        const detectionsTableBody = document.getElementById("detections-table-body");
        detectionsTableBody.innerHTML = detectionData.length > 0 ? detectionData
            .map(
                (detection) => `
                <tr>
                    <td>${detection.category}</td>
                    <td>${detection.label}</td>
                    <td>${detection.confidence.toFixed(2)}</td>
                </tr>
            `
            )
            .join("") : `
                <tr>
                    <td colspan="3">No detections available</td>
                </tr>
            `;
    } catch (error) {
        console.error("Error updating detection data:", error);
        const detectionsTableBody = document.getElementById("detections-table-body");
        detectionsTableBody.innerHTML = `
            <tr>
                <td colspan="3">Error loading detections</td>
            </tr>
        `;
        const detectionInsights = document.getElementById("detection-insights");
        detectionInsights.innerHTML = `<p>Error loading detection insights</p>`;
    }
}

// Periodically update detection data
document.addEventListener('DOMContentLoaded', () => {
    updateDetectionData();
    setInterval(updateDetectionData, 5000); // Update every 5 seconds
});