import click


@click.group()
def cli():
    pass


@cli.command()
def delete_video():
    click.echo('Delete old video')
