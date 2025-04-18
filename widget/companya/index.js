document.addEventListener('DOMContentLoaded', function() {
  const nameInput = document.getElementById('nameInput');
  const contentInput = document.getElementById('contentInput');
  const addButton = document.getElementById('addButton');
  const itemList = document.getElementById('itemList');

  addButton.addEventListener('click', function() {
      const name = nameInput.value.trim();
      const content = contentInput.value.trim();
      
      if (name && content) {
          addItem(name, content);
          nameInput.value = '';
          contentInput.value = '';
      }
  });

  function addItem(name, content) {
      const li = document.createElement('li');
      li.setAttribute('data-name', name);
      
      const nameSpan = document.createElement('span');
      nameSpan.textContent = name + ': ';
      
      const contentSpan = document.createElement('span');
      contentSpan.textContent = content;
      
      const deleteButton = document.createElement('button');
      deleteButton.textContent = 'Delete';
      deleteButton.addEventListener('click', function() {
          deleteItem(name);
      });
      
      li.appendChild(nameSpan);
      li.appendChild(contentSpan);
      li.appendChild(deleteButton);
      itemList.appendChild(li);
  }

  function deleteItem(name) {
      const item = document.querySelector(`li[data-name="${name}"]`);
      if (item) {
          item.remove();
      }
  }

  // Make functions available globally
  window.addItem = addItem;
  window.deleteItem = deleteItem;
});