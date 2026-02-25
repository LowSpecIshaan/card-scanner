const lead = JSON.parse(sessionStorage.getItem("leadData"));

if (lead) {
    document.getElementById("name").value = lead.name || "";
    document.getElementById("designation").value = lead.designation || "";
    document.getElementById("company").value = lead.company || "";
    document.getElementById("phone").value = lead.phone || "";
    document.getElementById("phone2").value = lead.phone2 || "";
    document.getElementById("email").value = lead.email || "";
    document.getElementById("address").value = lead.address || "";
    document.getElementById("website").value = lead.website || "";
}

function toggleOtherCustomer() {
    const dropdown = document.getElementById("customerType");
    const otherDiv = document.getElementById("otherCustomerDiv");
    const otherInput = document.getElementById("otherCustomerType");

    if (dropdown.value === "Others") {
        otherDiv.style.display = "block";
        otherInput.required = true; 
    } else {
        otherDiv.style.display = "none";
        otherInput.required = false;
        otherInput.value = "";
    }
}

function save() {

    let customerType = document.getElementById("customerType").value;

    if (customerType === "Others") {
        customerType = document.getElementById("otherCustomerType").value;
    }

    const data = {
        name: document.getElementById("name").value,
        designation: document.getElementById("designation").value,
        company: document.getElementById("company").value,
        customer_type: customerType,
        phone: document.getElementById("phone").value,
        phone2: document.getElementById("phone2").value,
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
            sessionStorage.removeItem("leadData");
            window.location.href = "/scan";
        } else {
            alert(response.error);
            sessionStorage.removeItem("leadData");
        }

    })
    .catch(err => {
        console.error(err);
        alert("Server error");
    });
}