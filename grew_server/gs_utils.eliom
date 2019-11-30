open Conll
open Libgrew

module String_opt_map = Map.Make (struct type t = string option let compare = compare end)

(* ================================================================================ *)
exception Error of string

let (warnings: Yojson.Basic.t list ref) = ref []
let warn s = warnings := (`String s) :: !warnings

let wrap fct last_arg =
  warnings := [];
  let json =
    try
      let data = fct last_arg in
      match !warnings with
      | [] -> `Assoc [ ("status", `String "OK"); ("data", data) ]
      | l -> `Assoc [ ("status", `String "WARNING"); ("messages", `List l); ("data", data) ]
    with
    | Error msg -> `Assoc [ ("status", `String "ERROR"); ("message", `String msg) ]
    | Conll_error t -> `Assoc [ ("status", `String "ERROR"); ("data", t) ]
    | Libgrew.Error t -> `Assoc [ ("status", `String "ERROR"); ("data", `String   t) ]
    | exc -> `Assoc [ ("status", `String "UNEXPECTED_EXCEPTION"); ("exception", `String (Printexc.to_string exc)) ] in
  json

(* ================================================================================ *)
(* Utils *)
(* ================================================================================ *)
module String_set = struct
  include Set.Make (String)
  let to_json t = `List (List.map (fun x -> `String x) (elements t))
end

module String_map = Map.Make (String)

let folder_iter fct folder =
  let dh = Unix.opendir folder in
  try
    while true do
      match Unix.readdir dh with
      | "." | ".." -> ()
      | x -> fct x
    done;
    assert false
  with
  | End_of_file -> Unix.closedir dh


module Log = struct
  let out_ch = ref stdout

  let time_stamp () =
    let gm = Unix.localtime (Unix.time ()) in
    Printf.sprintf "%02d_%02d_%02d_%02d_%02d_%02d"
      (gm.Unix.tm_year - 100)
      (gm.Unix.tm_mon + 1)
      gm.Unix.tm_mday
      gm.Unix.tm_hour
      gm.Unix.tm_min
      gm.Unix.tm_sec

  let _ =
    let filename = Printf.sprintf "grew_server_%s.log" (time_stamp ()) in
    out_ch := open_out filename

  let _info s = Printf.fprintf !out_ch "[%s] %s\n%!" (time_stamp ()) s
  let info s = Printf.ksprintf _info s
end