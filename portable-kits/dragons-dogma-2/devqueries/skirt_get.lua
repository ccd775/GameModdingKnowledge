local S = SR
if not S then return "no rec" end
json.dump_file("karin_dev/skirt_rec.json", { names = S.names, rows = S.rows })
return { frames = #S.rows, on = S.on }
