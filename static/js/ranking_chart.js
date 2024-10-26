// Function to fetch CSV file
const fetchCSV = async (csvFilePath) => {
    const response = await fetch(csvFilePath);
    const csvData = await response.text();
    return csvData;
};

// Load CSV file
const csvFilePath = '../../data/rank_progress/2024/progression2024_wk09_20231229_1023.csv';

// Parse CSV data
fetchCSV(csvFilePath).then((csvData) => {
    const parseCSV = (csv) => {
        const rows = csv.split('\n');
        const headers = rows[0].split(',');
        const data = rows.slice(1).map(row => row.split(','));
        return { headers, data };
    };
    
    // Get chart data for the first 15 players
    const { headers, data } = parseCSV(csvData);
    const first15PlayersData = data.slice(0, 5);

    // Function to dynamically update pointStyle based on player name
    const getPointStyle = (playerName) => {
        // Construct the image path based on the player name
        const imagePath = `../../data/player_img_test/${playerName}.jpg`;
        // const imagePath = `data/player_img_test/Nikola Jokić.jpg`;

        console.log('Image Path: ', imagePath)

        const playerImage = new Image();
        playerImage.src = imagePath;

        if (!imageExists(playerImage)) {
            // Log an error message (optional)
            console.error(`Image does not exist for ${playerName}. Defaulting to a different point style.`);

            // Set a default point style (e.g., 'circle' with a specified radius)
            return {
                pointStyle: 'circle',
                pointRadius: 20,
            };
        }

        // Create a derivative image with the desired resizing
        const resizedImage = createResizedImage(playerImage, 20); // Set the desired radius

        return {
            pointStyle: playerImage,
            // pointStyle: resizedImage,
            pointRadius: 15,
            pointHoverRadius: 30,
        };
    };

    // Function to create a resized image
    const createResizedImage = (originalImage, targetRadius) => {
        // Create a canvas element
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        // Set canvas dimensions based on target radius
        const canvasSize = 2 * targetRadius;
        canvas.width = canvasSize;
        canvas.height = canvasSize;

        // Draw the resized image on the canvas
        ctx.drawImage(
            originalImage,
            0,
            0,
            originalImage.width,
            originalImage.height,
            0,
            0,
            canvasSize,
            canvasSize
        );

        // Create a new Image object with the resized image
        const resizedImage = new Image();
        resizedImage.src = canvas.toDataURL();

        return resizedImage;
    };

    // Function to check if an image exists
    const imageExists = (image) => {
        return image.complete && image.naturalWidth !== 0;
    };
    
    // Prepare data for Chart.js
    const chartData = {
        labels: headers.slice(1), // Use weeks as labels
        datasets: first15PlayersData.map((playerRow, index) => ({
            label: playerRow[0],
            data: playerRow.slice(1).map((ranking, rankingIndex) => ({
                x: headers[rankingIndex + 1], // Use the week as x-coordinate
                y: parseInt(ranking),
            })),
            borderColor: `rgba(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255}, 1)`,
            fill: false,
            ...getPointStyle(playerRow[0]), // Dynamically set pointStyle based on player name
        })),
    };
    
    // Create chart
    const ctx = document.getElementById('mvpChart').getContext('2d');
    const myChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            plugins: {
                title: {
                    display: true,
                    text: '2024 NBA MVP Week-to-Week Rankings',
                    font: { size: 20 } // Adjust the title text size (you can toggle this value)
                },
                legend: {
                    display: true,
                    position: 'right',
                },
            },
            layout: {
                padding: {
                    left: 10, // Adjust the left padding
                    right: 20, // Adjust the right padding
                    top: 10, // Adjust the top padding
                    bottom: 10, // Adjust the bottom padding
                },
            },
            scales: {
                x: {
                    type: 'category', // Use category scale for x-axis
                    labels: headers.slice(1), // Add labels to the x-axis
                    position: 'top', // Move x-axis to the top
                },
                y: {
                    beginAtZero: false, // Start the y-axis from the lowest ranking
                    reverse: true, // Reverse the y-axis
                    max: 25, // Set the maximum value on the y-axis
                    ticks: {
                        stepSize: 1, // Display only integer values on the y-axis
                        precision: 0, // Ensure that there are no decimal places
                    },
                },
            },
        },
    });
});