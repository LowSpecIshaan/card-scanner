const id = document.body.dataset.id;

fetch(`/api/get/${id}`)
    .then(res => res.json())
    .then(data => {
        document.getElementById("name").value = data.name || "";
        document.getElementById("designation").value = data.designation || "";
        document.getElementById("company").value = data.company || "";
        document.getElementById("phone").value = data.phone || "";
        document.getElementById("phone2").value = data.phone2 || "";
        document.getElementById("email").value = data.email || "";
        document.getElementById("address").value = data.address || "";
        document.getElementById("website").value = data.website || "";

        const dropdown = document.getElementById("customerType");

        const customerTypes = [
            "",
            "Architect / Interior Designer",
            "Builder / Project",
            "Distributor / Trader",
            "Hospitality",
            "Offices / Commercial",
            "Showroom / Retail Brand",
            "Exhibitor"
        ];

        if (!customerTypes.includes(data.customer_type)) {
            dropdown.value = "Others";
            document.getElementById("otherCustomerType").value = data.customer_type || "";
        } else {
            dropdown.value = data.customer_type || "";
        }

        toggleOtherCustomer();
    });

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

    fetch(`/api/update/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(response => {

        if (response.status === "saved") {
            alert("Lead saved successfully!");
            window.location.href = "/leads";
        } else {
            alert(response.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Server error");
    });
}