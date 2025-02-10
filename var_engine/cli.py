from pathlib import Path

import click

from var_engine import plot_VaR
from var_engine.var_study import VaRStudy


@click.group()
def cli():
    pass


@click.command("var_study")
@click.argument("input_file", type=click.Path())
@click.option("-sd", "--start_date", "start_date", required=True, type=click.DateTime())
@click.option("-ed", "--end_date", "end_date", required=True, type=click.DateTime())
@click.option("-w", "--window", "window", default=365, type=int)
@click.option("-p", "--percentile", "percentile", default=0.95, type=float)
def var(input_file, **kwargs):
    input_file = Path(input_file)
    if not input_file.exists():
        raise click.BadParameter(f"Input file does not exist: {input_file}")

    my_study = VaRStudy(input_file)

    # Compute VaR
    my_result = my_study.compute(
        start_date=kwargs["start_date"].strftime(format='%Y-%m-%d'),
        end_date=kwargs["end_date"].strftime(format='%Y-%m-%d'),
        window=kwargs["window"],
        percentile=kwargs["percentile"],
    )

    # Print the result
    fig = plot_VaR(my_result)
    fig.show()


cli.add_command(var)

if __name__ == "__main__":
    cli()
