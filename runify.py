from argparse import ArgumentParser
from decouple import config
from pandas import DataFrame
from pprint import PrettyPrinter
from spotipy import Spotify
from spotipy import SpotifyOAuth

pp = PrettyPrinter(indent=2)

class Runify:

    def __init__(self) -> None:

        client_id = config('SPOTIPY_CLIENT_ID')
        client_secret = config('SPOTIPY_CLIENT_SECRET')
        redirect_uri = config('SPOTIPY_URI')
        client_scopes = config('SPOTIPY_SCOPES').split(',')
        self.sp_username = config('SPOTIFY_USERNAME')

        self.sp = Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                               client_secret=client_secret,
                                               redirect_uri=redirect_uri,
                                               scope=client_scopes))
    
    def run_the_track(self, source_playlist, playlist_name):
        
        candidate_tracks = self.get_playlist_tracks(source_playlist)
        candidate_features = self.get_track_features(candidate_tracks)
        running_tracks = self.filter_running_tracks(candidate_features)
        sorted = self.sort_playlist(running_tracks)
        self.generate_playlist(playlist_name, sorted)
        
    def get_playlist_tracks(self, playlist):

        if playlist[:5] == 'https':
            playlist_id = playlist[-10:]
        else:
            playlist_id = playlist
    
        results = self.sp.playlist_tracks(playlist_id)
        tracks = results['items']

        while results['next']:
            results = self.sp.next(results)
            tracks.extend(results['items'])

        return tracks
    
    def get_track_features(self, tracks):

        track_data = {}

        for t in tracks:
            id = t['track']['id']
            track_data[id] = {
                'track': self.sp.track(id),
                'feats': self.sp.audio_analysis(id)
            }

        return track_data

    def filter_running_tracks(self, track_data, lower_bound=150, upper_bound=180):
        
        running_tracks = {}
        idx = 0

        for k, v in track_data.items():
            id = k
            title = v['track']['name']
            tempo = v['feats']['track']['tempo']

            if tempo > (lower_bound/2) and tempo < (upper_bound/2):
                running_tracks[idx] = [id, tempo*2, title]

            elif tempo > lower_bound and tempo < upper_bound:
                running_tracks[idx] = [id, tempo, title]
            
            idx += 1
        
        return running_tracks

    def sort_playlist(self, running_tracks):

        df = DataFrame(running_tracks).T
        df.rename(columns={0: 'id', 1:'tempo', 2: 'title'}, inplace=True)
        return df.sort_values('tempo')

    def generate_playlist(self, playlist_name, df):
        
        new_pl = self.sp.user_playlist_create(self.sp_username, playlist_name)
        for rec in df['id']:
            self.sp.user_playlist_add_tracks(self.sp_username, new_pl['id'], [rec])

if __name__ == '__main__':

    dj = Runify()

    parser = ArgumentParser()

    parser.add_argument('--url', type=str, required=True, help='URL of Source Playlist')
    parser.add_argument('--name', type=str, required=True, help='Give it a name')

    args = parser.parse_args()
    
    playlist_url = args.url
    playlist_name = args.name

    dj.run_the_track(playlist_url, playlist_name)
