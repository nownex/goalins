const menuBtn = document.getElementById("menuBtn");
const nav = document.getElementById("nav");

if (menuBtn && nav) {

    menuBtn.addEventListener("click", () => {

        const isOpen = nav.classList.toggle("active");

        menuBtn.setAttribute(
            "aria-expanded",
            isOpen ? "true" : "false"
        );

    });

    nav.querySelectorAll("a").forEach(link => {

        link.addEventListener("click", () => {

            nav.classList.remove("active");

            menuBtn.setAttribute(
                "aria-expanded",
                "false"
            );

        });

    });

}
