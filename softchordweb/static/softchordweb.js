function SongTableCtrl($scope, $http) {
  $scope.current_song = {title:""};
  $scope.current_html = "";
  
  $scope.songs = [];
  
  $http.get('/songs/').success(function(data) {
      $scope.songs = data;
  });

  
  $scope.loadSong = function(number) {
    var curr_song = 0;
    angular.forEach($scope.songs, function(song) {
      if (song.number == number)
          curr_song = song;
    });
    
    $scope.current_song = curr_song;
    if($scope.current_song) {  
        $http.get('/songs/' + curr_song.number).success(function(data) {
            $scope.current_html = data;
        });
    }
    
  };

 
}

