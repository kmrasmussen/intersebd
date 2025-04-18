(function() {
  // Ensure the DOM is loaded before trying to add elements
  document.addEventListener('DOMContentLoaded', function() {

      // Create the widget button element
      const widgetButton = document.createElement('button');

      // Style the button
      widgetButton.textContent = '⭐'; // Star emoji as the icon
      widgetButton.style.position = 'fixed';
      widgetButton.style.bottom = '20px';
      widgetButton.style.right = '20px';
      widgetButton.style.fontSize = '24px';
      widgetButton.style.padding = '10px 15px';
      widgetButton.style.border = 'none';
      widgetButton.style.borderRadius = '50%'; // Make it circular
      widgetButton.style.backgroundColor = '#007bff'; // Example blue background
      widgetButton.style.color = 'white';
      widgetButton.style.cursor = 'pointer';
      widgetButton.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
      widgetButton.style.zIndex = '1000'; // Ensure it's on top

      // Add click event listener
      widgetButton.addEventListener('click', function() {
          // Use the standard prompt dialog
          const userInput = prompt("Ask the assistant anything:");

          // Check if the user entered something and didn't cancel
          if (userInput !== null && userInput.trim() !== "") {
              // Check if sendMessage function is available globally
              if (typeof window.sendMessage === 'function') {
                  console.log(`Little Widget: Sending message: "${userInput}"`);
                  window.sendMessage(userInput);
              } else {
                  console.error("Little Widget: sendMessage function is not available.");
                  alert("Error: Cannot send message. The core widget script might not be loaded correctly.");
              }
          } else {
              console.log("Little Widget: User cancelled or entered empty message.");
          }
      });

      // Append the button to the body
      document.body.appendChild(widgetButton);

      console.log("Little Widget added to the page.");

  });
})(); // Immediately Invoked Function Expression (IIFE) to avoid polluting global scope unnecessarily