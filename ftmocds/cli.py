import json
import click
from followthemoney.cli.cli import cli
from followthemoney.cli.util import write_object

from ftmocds.convert import convert_record


@cli.command('import-ocds', help="Import open contracting (OCDS) data")
@click.option('-i', '--infile', type=click.File('r'), default='-')  # noqa
@click.option('-o', '--outfile', type=click.File('w'), default='-')  # noqa
def import_ocds(infile, outfile):
    try:
        while True:
            line = infile.readline()
            if not line:
                return
            record = json.loads(line)
            for entity in convert_record(record):
                if entity.id is not None:
                    write_object(outfile, entity)
    except BrokenPipeError:
        raise click.Abort()
