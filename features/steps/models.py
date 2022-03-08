from behave import *

from classroom_video import models


@given('we have a model `{model_name}` defined')
def step_impl(context, model_name):
    assert hasattr(models, model_name)
    context.model = getattr(models, model_name)
    context.properties = context.model.schema()["properties"]

@then('the model has property `{property_name}`')
def step_impl(context, property_name):
    assert context.model is not None
    properties = context.properties
    assert property_name in properties
