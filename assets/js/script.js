document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search');
    const calculatorItems = document.querySelectorAll('.calculator-item');

    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();

        calculatorItems.forEach(item => {
            const calculatorName = item.textContent.toLowerCase();
            if (calculatorName.includes(searchTerm)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    });
});

