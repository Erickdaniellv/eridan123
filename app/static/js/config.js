// Función para abrir o cerrar el menú de navegación
function toggleNav() {
    document.getElementById("myNav").classList.toggle("menu_width");
    document.querySelector(".custom_menu-btn").classList.toggle("menu_btn-style");
  }
  
  // Función para cerrar específicamente el menú de navegación
  function closeNav() {
    document.getElementById("myNav").classList.remove("menu_width");
    document.querySelector(".custom_menu-btn").classList.remove("menu_btn-style");
  }
  
  // Función de desplazamiento suave modificada para cerrar el menú
  function desplazarSuave(id) {
    const elemento = document.getElementById(id);
    elemento.scrollIntoView({ behavior: 'smooth' });
    closeNav(); // Asegúrate de cerrar el menú después del desplazamiento
  }
  