#!/usr/bin/sh

line="$(mysql --no-auto-rehash -D 'sipb-door+doorpi' -e 'select timestamp, status from door_status order by timestamp desc limit 1;' -ss -B)"
time="$(printf '%s' "${line}" | awk '{print $1}' | sed -E 's/.{9}$//')"
door="$(printf '%s' "${line}" | awk '{print $2}')"

case "${door}" in
	"1") # Closed
		state="closed"
		;;
	"0") # Open
		state="open"
		;;
	*) # Error?
		state="error"
		time="$(date '+%s')"
		;;
esac

file="door-is-${state}.png"

base="door"
if [ "$(date '+%m%d')" = "0401" ]; then
	base="windows"
fi

image="images/${base}-${state}.png"
if [ ! -e "${image}" ]; then
	base="door"
	image="images/door-${state}.png"
fi

touch -d "@${time}" door.time
if [ door.time -nt door-is-*.png ] || [ ! -e "${file}" ]; then
	date="$(date -d "@${time}" '+%a %b %d %H:%M:%S %Y')"
	rm -f door-is-*.png
	convert \
		-background '#eeeeee00' \
		-font "$(fc-match --format='%{file}' 'Open Sans')" \
		-gravity center \
		"label:${state} since" \
		"${image}" \
		label:"${date}" \
		-append \
		"${file}"
fi

printf 'Location: %s\n' "${file}"
printf 'Content-type: image/png\n'
printf '\n'

cat "${file}"
