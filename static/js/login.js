function login() {
    const requestOptions = {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify({
            id: document.getElementById("id").value,
            password: document.getElementById("password").value
        })
    }
    fetch("/api/login", requestOptions)
        .then(response => response.json())
        .then(data => {
            if (data.status === "logged_in") {
                alert("Logged in successfully!")
                window.location.href = "/";
            } else {
                alert("Invalid Credentials");
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("Something went wrong");
        });
}

function togglePassword() {
    const input = document.getElementById("password");
    const eye = document.getElementById("eyeIcon");

    if (input.type === "password") {
        input.type = "text";
        eye.classList.remove("fa-eye");
        eye.classList.add("fa-eye-slash");
    } else {
        input.type = "password";
        eye.classList.remove("fa-eye-slash");
        eye.classList.add("fa-eye");
    }
}