Feature: API has models with properties to be stored in database

  Scenario: Video Model
     Given we have a model `Video` defined
     Then the model has property `timestamp`
     Then the model has property `meta`

   Scenario: VideoMeta Model
      Given we have a model `VideoMeta` defined
      Then the model has property `environment_id`
      Then the model has property `camera_id`
      Then the model has property `path`
      Then the model has property `duration_seconds`
      Then the model has property `fps`

  Scenario: ExistingVideo Model
     Given we have a model `ExistingVideo` defined
     Then the model has property `id`
     Then the model has property `timestamp`
     Then the model has property `meta`
