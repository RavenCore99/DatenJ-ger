lucide && lucide.createIcons?.();

const form = document.getElementById("msf");
const steps = Array.from(document.querySelectorAll(".step"));
const backBtn = document.getElementById("backBtn");
const nextBtn = document.getElementById("nextBtn");
const submitBtn = document.getElementById("submitBtn");
const progress = document.getElementById("progress");
const dots = Array.from(document.querySelectorAll(".step-dot"));
const success = document.getElementById("success");

let current = 0;

// Simple validators
const rules = {
  0: () => {
    const email = form.email;
    const pass = form.password;
    const tos = document.getElementById("tos1");
    let ok = true;

    const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value);
    toggleError("email", !validEmail);
    ok = ok && validEmail;

    const validPass = (pass.value || "").length >= 8;
    toggleError("password", !validPass);
    ok = ok && validPass;

    ok = ok && tos.checked;
    return ok;
  },
  1: () => {
    const name = form.fullname.value.trim().length > 1;
    toggleError("fullname", !name);

    const role = form.role.value.trim().length > 0;
    toggleError("role", !role);

    return name && role;
  },
  2: () => {
    const consent = document.getElementById("consent").checked;
    toggleError("consent", !consent);
    return consent;
  }
};

function toggleError(key, show) {
  const el = document.querySelector(`[data-error="${key}"]`);
  if (!el) return;
  el.classList.toggle("hidden", !show);
}

function showStep(i) {
  steps.forEach((s, idx) => {
    s.classList.toggle("hidden", idx !== i);
  });
  // Buttons
  backBtn.disabled = i === 0;
  nextBtn.classList.toggle("hidden", i === steps.length - 1);
  submitBtn.classList.toggle("hidden", i !== steps.length - 1);

  // Progress & dots
  const pct = (i / (steps.length - 1)) * 100;
  progress.style.width = `${pct}%`;
  dots.forEach((d, idx) => {
    d.className = `step-dot h-8 w-8 rounded-full grid place-items-center border 
         ${
           idx <= i
             ? "bg-white/20 border-white/40"
             : "bg-white/10 border-white/20"
         }`;
  });

  // Review data on step 3
  if (i === 2) {
    document.getElementById("r-email").textContent = form.email.value || "—";
    document.getElementById("r-fullname").textContent =
      form.fullname.value || "—";
    document.getElementById("r-role").textContent = form.role.value || "—";
    document.getElementById("r-phone").textContent = form.phone.value || "—";
  }
}

nextBtn.addEventListener("click", () => {
  const validate = rules[current] ?? (() => true);
  if (!validate()) return;
  current = Math.min(current + 1, steps.length - 1);
  showStep(current);
});

backBtn.addEventListener("click", () => {
  current = Math.max(current - 1, 0);
  showStep(current);
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const validate = rules[current] ?? (() => true);
  if (!validate()) return;

  // Fake async submit UX
  submitBtn.disabled = true;
  submitBtn.textContent = "Submitting…";
  setTimeout(() => {
    form.classList.add("hidden");
    success.classList.remove("hidden");
  }, 700);
});

// Initial paint
showStep(0);
