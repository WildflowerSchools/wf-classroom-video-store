Feature: API is a web API

  Scenario: Upload Videos Endpoint
      Given a `POST` method to `http://127.0.0.1:2300/videos`
      and a set of videos
       | video_path                 | environment_id                       | assignment_id                        | camera_id                            | duration_seconds | fps | timestamp                    | path                                                                                                    |
       | features/files/video-a.txt | a44cb30b-3107-4dad-8a86-3a0f17c36cb3 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 10               | 10  | 2021-05-27T17:00:00.000+0000 | a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/2021/05/27/17/02-00.mp4 |
       | features/files/video-b.txt | a44cb30b-3107-4dad-8a86-3a0f17c36cb3 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 10               | 10  | 2021-05-27T17:00:10.000+0000 | a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/2021/05/27/17/02-12.mp4 |
       | features/files/video-b.txt | a44cb30b-3107-4dad-8a86-3a0f17c36cb3 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 10               | 10  | 2021-05-27T17:00:10.000+0000 | a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/2021/05/27/17/02-55.mp4 |
      When calling the request
      Then API returns videos with ids
