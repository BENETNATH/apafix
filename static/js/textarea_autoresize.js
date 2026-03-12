document.addEventListener('DOMContentLoaded', function() {
    
    /**
     * La fonction principale qui ajuste la hauteur d'un <textarea> à son contenu.
     * @param {HTMLElement} textarea - L'élément textarea à redimensionner.
     */
    function adjustTextareaHeight(textarea) {
        if (textarea && textarea.style) {
            // Réinitialise temporairement la hauteur pour permettre au navigateur de calculer
            // la hauteur de défilement (scrollHeight) naturelle.
            textarea.style.height = 'auto';
            
            // Applique la hauteur de défilement à la hauteur de l'élément,
            // ce qui l'étend pour s'adapter à tout le texte.
            textarea.style.height = (textarea.scrollHeight) + 'px';
        }
    }

    // --- Action 1 : Redimensionnement dynamique lorsque l'utilisateur tape ---
    // C'est le comportement existant, qui reste utile.
    document.querySelectorAll('textarea.form-control').forEach(function(textarea) {
        textarea.addEventListener('input', function() {
            adjustTextareaHeight(this);
        });
    });

    // --- Action 2 (LA SOLUTION) : Redimensionnement à l'ouverture d'une section de l'accordéon ---
    // On cible l'accordéon principal par son ID.
    const accordion = document.getElementById('xmlFormAccordion');
    if (accordion) {
        // Bootstrap déclenche l'événement 'shown.bs.collapse' juste après qu'une section soit devenue visible.
        accordion.addEventListener('shown.bs.collapse', function (event) {
            // 'event.target' est le contenu de la section qui vient de s'ouvrir.
            const newlyVisiblePanel = event.target;
            
            // On trouve tous les <textarea> à l'intérieur de cette section maintenant visible.
            const textareasInPanel = newlyVisiblePanel.querySelectorAll('textarea.form-control');

            // On applique la fonction de redimensionnement à chacun d'eux.
            textareasInPanel.forEach(adjustTextareaHeight);
        });
    }

    // --- Action 3 : Redimensionnement initial pour les champs déjà visibles ---
    // Au cas où une section serait ouverte par défaut ou qu'il y ait des textarea en dehors de l'accordéon.
    document.querySelectorAll('textarea.form-control').forEach(adjustTextareaHeight);

});