const maxOfficers = 6;

function addOfficerField() {
    if (officerCount >= maxOfficers) {
        alert('Maksimal 6 petugas dapat dipilih!');
        return;
    }

    officerCount++;
    console.log('Adding officer field, new officerCount:', officerCount);
    const officerFields = document.getElementById('officerFields');
    const newField = document.createElement('div');
    newField.className = 'officer-field';

    const select = document.createElement('select');
    select.name = `officer_names_${officerCount}`;
    select.className = 'officer-select';

    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.text = 'Pilih Petugas';
    defaultOption.selected = true;
    select.appendChild(defaultOption);

    officersFromServer.forEach(officer => {
        const option = document.createElement('option');
        option.value = officer;
        option.text = officer;
        select.appendChild(option);
    });

    newField.appendChild(select);

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-remove-officer';
    removeBtn.innerText = 'Hapus';
    removeBtn.onclick = function () { removeOfficerField(removeBtn); };
    newField.appendChild(removeBtn);

    officerFields.appendChild(newField);
    updateOfficerOptions();

    if (officerCount >= maxOfficers) {
        const addButton = document.querySelector('.btn-add-officer');
        if (addButton) addButton.style.display = 'none';
    }
}

function removeOfficerField(button) {
    if (officerCount > 1) {
        button.parentElement.remove();
        officerCount--;
        console.log('Removing officer field, new officerCount:', officerCount);
        updateOfficerOptions();

        const addButton = document.querySelector('.btn-add-officer');
        if (addButton) addButton.style.display = 'block';
    }
}

function updateOfficerOptions() {
    console.log('Updating officer options');
    const selects = document.querySelectorAll('.officer-select');
    const selectedValues = Array.from(selects)
        .map(s => s.value)
        .filter(v => v !== '');

    selects.forEach(select => {
        const currentValue = select.value;
        select.innerHTML = '';

        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.text = 'Pilih Petugas';
        if (!currentValue) defaultOption.selected = true;
        select.appendChild(defaultOption);

        officersFromServer.forEach(officer => {
            if (!selectedValues.includes(officer) || officer === currentValue) {
                const option = document.createElement('option');
                option.value = officer;
                option.text = officer;
                if (officer === currentValue) option.selected = true;
                select.appendChild(option);
            }
        });
    });
}

document.addEventListener('change', (event) => {
    if (event.target.classList.contains('officer-select')) {
        console.log('Dropdown changed, updating options');
        updateOfficerOptions();
    }
});

if (officerCount >= maxOfficers) {
    const addButton = document.querySelector('.btn-add-officer');
    if (addButton) addButton.style.display = 'none';
}