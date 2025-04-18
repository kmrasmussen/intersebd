(function() {
  // Ensure the DOM is loaded before trying to add elements
  document.addEventListener('DOMContentLoaded', function() {

      // Create the widget button element
      const widgetButton = document.createElement('button');

      // Assign the CSS class instead of setting inline styles
      widgetButton.className = 'brainy-widget-button';

      // Add click event listener
      widgetButton.addEventListener('click', function() {
          // Use the standard prompt dialog
          const userInput = prompt("Ask the assistant anything:");

          // Check if the user entered something and didn't cancel
          if (userInput !== null && userInput.trim() !== "") {
              // Check if sendMessage function is available globally
              if (typeof window.sendMessage === 'function') {
                  console.log(`Brainy Widget: Sending message: "${userInput}"`);
                  window.sendMessage(userInput);
              } else {
                  console.error("Brainy Widget: sendMessage function is not available.");
                  alert("Error: Cannot send message. The core widget script might not be loaded correctly.");
              }
          } else {
              console.log("Brainy Widget: User cancelled or entered empty message.");
          }
      });

      // Append the button to the body
      document.body.appendChild(widgetButton);

      console.log("Brainy Widget added to the page.");

  });
})();