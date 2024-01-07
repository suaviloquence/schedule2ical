from .schedule2ical import parse_schedule, get_html, generate_schedule 

def run_cli():
    html = get_html("TODO")
    courses =  parse_schedule(html)
    schedule = generate_schedule(courses, "mcarr35")
    print(schedule)

if __name__ == '__main__':
    run_cli()
