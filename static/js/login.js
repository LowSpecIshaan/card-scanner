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
    const button = event.target;

    if (input.type === "password") {
        input.type = "text";
        button.innerText = "Hide Password";
    } else {
        input.type = "password";
        button.innerText = "Show Password";
    }
}