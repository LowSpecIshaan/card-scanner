const video = document.getElementById("camera");

navigator.mediaDevices.getUserMedia({
    video: {
        facingMode: "environment",
        width: { ideal: 960 },
        height: { ideal: 720 }
    },
    audio: false
})
    .then(stream => {
        document.getElementById("camera").srcObject = stream;
    })
    .catch(err => console.error(err));

function scan(){
    const canvas = document.getElementById("snapshot");
    const ctx = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.drawImage(video, 0, 0);

    canvas.toBlob(blob => {
        const formData = new FormData();
        formData.append("image", blob, "card.jpg");

        fetch("/api/scan", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if(data.status === "success"){
                console.log(data)
                sessionStorage.setItem("leadData", JSON.stringify(data));
                window.location.href = "/form"
            }else{
                alert("Scan Failed.");
            }
        })
        .catch(err => console.error(err));
    }, "image/jpeg", 0.9);
}