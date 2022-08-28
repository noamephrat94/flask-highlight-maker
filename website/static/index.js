function deleteNote(noteId){
    fetch("/delete-note",{
        method: "POST",
        body: JSON.stringify({ noteId: noteId}),
    }).then((_res) => {
        window.location.href = "/";
    });
}

function deleteVideo(videoId){
    fetch("/delete-video",{
        method: "POST",
        body: JSON.stringify({ videoId: videoId}),
    }).then((_res) => {
        window.location.href = "/";
    });
}

function loader(){
    document.getElementById("loader_before").innerHTML = "Processing your video, please dont leave the page and stay connected to the internet";
}

function myFunction() {
    document.getElementById("demo2").innerHTML = "Processing your video, please dont leave the page and stay connected to the internet";
    document.getElementById("demo").className = 'loader_before';
    document.getElementById("gen_btn").className = 'generate_btn2';
  }



