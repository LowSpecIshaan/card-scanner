const lead = JSON.parse(sessionStorage.getItem("leadData"));

if (lead) {
    document.getElementById("name").value = lead.name || "";
    document.getElementById("designation").value = lead.designation || "";
    document.getElementById("company").value = lead.company || "";
    document.getElementById("phone").value = lead.phone || "";
    document.getElementById("email").value = lead.email || "";
    document.getElementById("address").value = lead.address || "";
    document.getElementById("website").value = lead.website || "";
}

function save() {

    const data = {
        name: document.getElementById("name").value,
        designation: document.getElementById("designation").value,
        company: document.getElementById("company").value,
        phone: document.getElementById("phone").value,
        email: document.getElementById("email").value,
        address: document.getElementById("address").value,
        website: document.getElementById("website").value,
        remarks: document.getElementById("remarks").value
    };

    fetch("/api/save", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(response => {

        if (response.status === "saved") {
            alert("Lead saved successfully!");
            window.location.href = "/scan";
        } else {
            alert(response.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Server error");
    });
}