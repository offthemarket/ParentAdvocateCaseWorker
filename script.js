// Dropdown open / close
document.querySelectorAll(".pa-nav-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
        const section = btn.closest(".pa-nav-section");
        section.classList.toggle("open");
    });
});

// Hint text on hover
const hintBox = document.getElementById("pa-hint");

document.querySelectorAll(".pa-nav-list li").forEach((item) => {
    item.addEventListener("mouseenter", () => {
        const text = item.getAttribute("data-hint");
        if (text && hintBox) {
            hintBox.textContent = text;
        }
    });

    item.addEventListener("mouseleave", () => {
        if (hintBox) {
            hintBox.textContent =
                "Hover over a menu item to see what it does.";
        }
    });
});
