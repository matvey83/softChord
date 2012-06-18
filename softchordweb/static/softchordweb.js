function SongTableCtrl($scope, $http) {
  $scope.current_song = {title:"NONE"};
  $scope.current_html = "";
  
  $scope.songs = [];
  
  $http.get('/songs/').success(function(data) {
      $scope.songs = data;
  });

  $scope.addTodo = function() {
    $scope.songs.push({title:$scope.todoText, number:0, id:0});
    $scope.todoText = '';
  };
  
  $scope.loadSong = function(number) {
    var curr_song = 0;
    angular.forEach($scope.songs, function(song) {
      if (song.number == number)
          curr_song = song;
    });
    
    $scope.current_song = curr_song;
    if($scope.current_song) {  
        $http.get('/songs/%i' % curr_song.number).success(function(data) {
            $scope.current_html = data;
            //$scope.current_html = curr_song.text;
        });
    }
    
  };

 
  $scope.archive = function() {
    var oldSong = $scope.songs;
    $scope.songs = [];
    angular.forEach(oldSong, function(todo) {
      if (!todo.done) $scope.songs.push(todo);
    });
  };


}

