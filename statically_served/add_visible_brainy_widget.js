(function() {
    // Function to create and add the widget
    function createBrainyWidget() {
      // Check if the widget already exists to avoid duplicates
      if (document.getElementById('brainy-widget-button')) {
        console.log("Brainy Widget already exists on the page.");
        return;
      }
      
      // Create a new div element for the circle
      const circle = document.createElement('div');
      
      // Set a unique ID to avoid style conflicts
      circle.id = 'brainy-widget-button';
      
      // Apply styles to make it a circle fixed in the bottom right
      Object.assign(circle.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        width: '50px',
        height: '50px',
        borderRadius: '50%',
        backgroundColor: 'rgba(128, 128, 128, 0.8)', // Gray color
        color: 'white',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        cursor: 'pointer',
        boxShadow: '0 2px 10px rgba(0, 0, 0, 0.2)',
        zIndex: '9999',
        transition: 'transform 0.3s ease, background-color 0.3s ease',
        border: 'none', // Remove button border
        outline: 'none', // Remove outline
        padding: '0' // Remove padding
      });
      
      // Create a pseudo-element for the brain emoji
      const styleId = 'brainy-widget-style';
      if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
          #brainy-widget-button::before {
            content: '🧠';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 24px;
            font-family: 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif;
          }
        `;
        document.head.appendChild(style);
      }
      
      // Add hover effect
      circle.onmouseenter = function() {
        this.style.transform = 'scale(1.1)';
        this.style.backgroundColor = 'rgba(105, 105, 105, 0.9)'; // Darker gray on hover
      };
      
      circle.onmouseleave = function() {
        this.style.transform = 'scale(1)';
        this.style.backgroundColor = 'rgba(128, 128, 128, 0.8)'; // Back to original gray
      };
      
      // Add click event to show prompt and use sendMessage function
      circle.onclick = function() {
        console.log('Brainy Widget: Button clicked');
        
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
      };
      
      // Add the circle to the document body
      document.body.appendChild(circle);
      
      console.log("Brainy Widget added to the page.");
    }
  
    // If the DOM is already loaded, create the widget immediately
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', createBrainyWidget);
    } else {
      createBrainyWidget();
    }
  })();