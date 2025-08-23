// script.js
let medicines = [];
let selectedMeds = new Set();
setInterval(checkReminders, 60000); // every 1 minute


function register() {
  alert("Registration successful (simulated)");
  switchToApp();
}

function login() {
  alert("Login successful (simulated)");
  switchToApp();
  if (Notification.permission !== "granted") {
  Notification.requestPermission();
}

 // Start the reminder check only after login
  if (!window.reminderInterval) {
    window.reminderInterval = setInterval(checkReminders, 60000);
  }

}

function logout() {
  document.getElementById("auth-section").classList.remove("hidden");
  document.getElementById("app-section").classList.add("hidden");
  medicines = [];
  selectedMeds.clear();
  renderList();
  clearInterval(window.reminderInterval);
  window.reminderInterval = null;
  medicines.forEach(med => {
  med.confirmed = false;
  med.lastNotified = null;
});

}

function deleteAccount() {
  if (confirm("Are you sure you want to delete your account?")) {
    logout();
    alert("Account deleted (simulated)");
  }
}

function switchToApp() {
  document.getElementById("auth-section").classList.add("hidden");
  document.getElementById("app-section").classList.remove("hidden");
}

function addMedicine() {
  const name = document.getElementById("medName").value;
  const meal = document.getElementById("mealType").value;
  const start = document.getElementById("startTime").value;
  const end = document.getElementById("endTime").value;
  const freq = parseInt(document.getElementById("frequency").value);
  const unit = document.getElementById("frequencyUnit").value;

  if (!name || !start || !end || isNaN(freq) || freq <= 0) {
    alert("Please fill out all fields correctly.");
    return;
  }

  const exists = medicines.some(med => med.name === name);
  if (exists) {
    alert("Medicine with this name already exists.");
    return;
  }

  medicines.push({
    name,
    meal,
    start,
    end,
    freq,
    unit,
    confirmed: false,
    lastNotified: null
  });
  renderList();
  clearInputs();
}

function renderList() {
  const list = document.getElementById("medList");
  list.innerHTML = "";

  medicines.forEach((med, i) => {
    const li = document.createElement("li");
    const isSelected = selectedMeds.has(i);
    li.style.background = isSelected ? "#d1ecf1" : "#e0f7fa";

    li.innerHTML = `
      <div>
        <strong>${med.name}</strong> (${med.meal})<br>
        ${med.start} - ${med.end}, every ${med.freq} ${med.unit}
      </div>
      <div>
        <input type="checkbox" onchange="toggleSelect(${i})" ${isSelected ? "checked" : ""}/>
      </div>
    `;
    list.appendChild(li);
  });
}

function toggleSelect(index) {
  if (selectedMeds.has(index)) {
    selectedMeds.delete(index);
  } else {
    selectedMeds.add(index);
  }
  renderList();
}

function deleteSelected() {
  if (selectedMeds.size === 0) {
    alert("No medicines selected for deletion.");
    return;
  }
  if (confirm("Delete selected medicines?")) {
    medicines = medicines.filter((_, idx) => !selectedMeds.has(idx));
    selectedMeds.clear();
    renderList();
  }
}

function confirmSelected() {
  selectedMeds.forEach(idx => {
    medicines[idx].confirmed = true;
  });
  alert("Selected medicines marked as taken.");
  selectedMeds.clear();
  renderList();
}

function clearInputs() {
  document.getElementById("medName").value = "";
  document.getElementById("startTime").value = "";
  document.getElementById("endTime").value = "";
  document.getElementById("frequency").value = "";
}

function checkReminders() {
  const now = new Date();
  const currentTime = now.toTimeString().substring(0, 5); // "HH:MM"

  medicines.forEach((med, i) => {
    if (med.confirmed) return;

    if (med.start <= currentTime && currentTime <= med.end) {
      if (!med.lastNotified || (now - new Date(med.lastNotified)) / 60000 >= med.freq) {
        notifyUser(med.name, med.meal);
        med.lastNotified = now.toISOString();
      }
    }
  });
}

function notifyUser(name, mealTime) {
  if (Notification.permission === "granted") {
    new Notification("⏰ Medication Reminder", {
      body: `Take ${name} (${mealTime} meal). Please confirm once taken.`,
      icon: "https://cdn-icons-png.flaticon.com/512/3601/3601650.png", // Optional icon
      silent: false
    });
  } else {
    alert(`🔔 Reminder: Take ${name} (${mealTime} meal).`);
  }
}

