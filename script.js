$(document).ready(function(){
    $(document).on("click",".nav-link",function(){
        $(".nav-link").removeClass("active");
        $(this).addClass("active");
    })
})