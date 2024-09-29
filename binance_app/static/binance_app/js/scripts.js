console.log("External JavaScript file is loaded!");

// function toggleDates() {
//     const historyDropdown = document.getElementById('history-dropdown');
//     const startDate = document.getElementById('start-date');
//     const endDate = document.getElementById('end-date');

//     if (historyDropdown.value === 'history') {
//         startDate.style.display = 'block';
//         endDate.style.display = 'block';
//     } else {
//         startDate.style.display = 'none';
//         endDate.style.display = 'none';
//     }
// }

// function toggleCategoryDivs() {
//     const categoryDropdown = document.getElementById('type-dropdown');
//     const spotOptions = document.getElementById('spot-options');
//     const futuresOptions = document.getElementById('futures-options');


//     if (categoryDropdown.value === 'spot') {
//         spotOptions.style.display = 'block';
//         futuresOptions.style.display = 'none';

//     } else if (categoryDropdown.value === 'futures') {
//         futuresOptions.style.display = 'block';
//         spotOptions.style.display = 'none';
//     }
// }



// function updateEndpoint() {
//     console.log("Dropdown change detected");
//     var category = document.getElementById("type-dropdown").value;
//     var endpointDropdown = document.getElementById("endpoint-dropdown");

//     // Clear existing options
//     endpointDropdown.innerHTML = "";

//     // Define endpoint options for each category
//     var spotEndpoints = [
//         { value: "account-information", text: "Account information" },
//         { value: "trade-list", text: "Trade list" },
//         { value: "all-orders", text: "All orders" },
//         { value: "universal-transfer-history", text: "Universal transfer history" },
//         { value: "flexible-product-position-data", text: "Flexible product position data" }
//     ];

//     var futuresEndpoints = [
//         { value: "account-information-user-data", text: "Account information user data" },
//         { value: "trade-list", text: "Trade list" },
//         { value: "position-information", text: "Position information" },
//         { value: "futures-account-balances", text: "Futures account balances" }
//     ];

//     var endpoints = [];

//     // Choose endpoints based on selected category
//     if (category === "spot") {
//         endpoints = spotEndpoints;
//     } else if (category === "futures") {
//         endpoints = futuresEndpoints;
//     }

//     // Populate the endpoint dropdown
//     endpoints.forEach(function(endpoint) {
//         var option = document.createElement("option");
//         option.value = endpoint.value;
//         option.text = endpoint.text;
//         endpointDropdown.appendChild(option);
//     });

//     // Add a default option if no category is selected
//     if (endpoints.length === 0) {
//         var defaultOption = document.createElement("option");
//         defaultOption.value = "";
//         defaultOption.text = "Select a category first";
//         endpointDropdown.appendChild(defaultOption);
//     }
// }







// function populateSymbolDropdown(symbols) {
// var symbolDropdown = document.getElementById("symbol");

// // Clear existing options (if any)
// symbolDropdown.innerHTML = '';

// // Add default option
// var defaultOption = document.createElement("option");
// defaultOption.text = 'Select Symbol';
// defaultOption.value = '';
// symbolDropdown.appendChild(defaultOption);

// // Add symbols as options
// symbols.forEach(function(symbol) {
// var option = document.createElement("option");
// option.text = symbol;
// option.value = symbol;
// symbolDropdown.appendChild(option);
// });
// }

// // Fetch symbols from Django backend
// async function fetchSymbols() {
// try {
// const response = await fetch('/get_binance_symbols/');
// if (!response.ok) {
//     throw new Error('Failed to fetch symbols');
// }
// const data = await response.json();
// if (data.symbols) {
//     populateSymbolDropdown(data.symbols);
// } else {
//     console.error('Error fetching symbols:', data.error);
// }
// } catch (error) {
// console.error('Error fetching symbols:', error);
// }
// }

// // Call function to fetch symbols and populate dropdown when page loads
// document.addEventListener('DOMContentLoaded', function() {
// fetchSymbols();
// });

// // Optionally, if the endpoint dropdown changes dynamically
// function toggleSymbolDropdown() {
// var endpointDropdown = document.getElementById("type-dropdown");
// var symbolDropdown = document.getElementById("symbol-dropdown");

// if (endpointDropdown.value === "recent_trades") {
// symbolDropdown.style.display = "block";
// fetchSymbols();  // Call function to fetch symbols
// } else {
// symbolDropdown.style.display = "none";
// }
// }

