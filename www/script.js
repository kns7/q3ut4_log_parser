chartColors = [
    'rgb(255, 99, 132)',
	'rgb(255, 159, 64)',
	'rgb(255, 205, 86)',
	'rgb(75, 192, 192)',
	'rgb(54, 162, 235)',
	'rgb(153, 102, 255)',
    'rgb(201, 203, 207)',
    'rgb(0, 238, 255)',
    'rgb(234, 98, 183)',
    'rgb(234, 100, 98)',
    'rgb(164, 234, 98)',
    'rgb(234, 98, 164)',
    'rgb(234, 121, 98)'
]

function getRandomColor() {
    var letters = '0123456789ABCDEF'.split('');
    var color = '#';
    for (var i = 0; i < 6; i++ ) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

function makeChart(player,datas,chart){
    
    numbers = [];
    weapons = [];
    for(let i in datas){
        numbers.push(datas[i])
        weapons.push(i)
    }
    switch(chart){
        case 'weapons': scheme = 'brewer.DarkTwo7'; break;
        case 'fraggedby': scheme = 'office.Badge6'; break;
        case 'fragged': scheme = 'office.Apothecary6'; break;
    }

    var ctx = document.getElementById(player + "_"+chart);
      var myChart = new Chart(ctx, {
        type: 'pie',
        data: {
            datasets: [{
              data: numbers
            }],
            labels: weapons
          },
        options: {
          responsive: false,
          plugins: {
              colorschemes: {
                  scheme: scheme
              }
          }
        }
    });
}


$(document).ready(function(){
    $(document).on("click",".nav-link",function(){
        $(".nav-link").removeClass("active");
        $(this).addClass("active");
    })
})