from django.db import models


class DBSong(models.Model):
    """
    Database Song table (each entry is a song)
    """
    id = models.AutoField(primary_key=True)
    text = models.CharField(max_length=1000, blank=True)
    title = models.TextField(blank=True)
    key_note_id = models.IntegerField(null=True, blank=True)
    key_is_major = models.NullBooleanField(null=True, blank=True)
    number = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = u'songs'
    def __unicode__(self):
        return self.title

class DBSongChord(models.Model):
    """
    Databse SongChord table (each entry is a chord assigned to a letter of a song)
    """
    id = models.AutoField(primary_key=True)
    song_id = models.IntegerField(null=True, blank=True)
    character_num = models.IntegerField(null=True, blank=True)
    note_id = models.IntegerField(null=True, blank=True)
    chord_type_id = models.IntegerField(null=True, blank=True)
    bass_note_id = models.IntegerField(null=True, blank=True)
    marker = models.TextField(blank=True)
    in_parentheses = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = u'song_chord_link'
