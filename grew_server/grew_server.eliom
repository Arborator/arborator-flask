[%%shared
    open Eliom_lib
    open Eliom_content
    open Html.D
    open Gs_types
]

[%%server
    open Conll
    open Libgrew
]

module Grew_server_app =
  Eliom_registration.App (
    struct
      let application_name = "grew_server"
      let global_data_path = None
    end)

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
      | Conll_types.Error t -> `Assoc [ ("status", `String "ERROR"); ("data", t) ]
      | Libgrew.Error t -> `Assoc [ ("status", `String "ERROR"); ("data", `String   t) ]
      | exc -> `Assoc [ ("status", `String "UNEXPECTED_EXCEPTION"); ("exception", `String (Printexc.to_string exc)) ] in
  json

(* -------------------------------------------------------------------------------- *)
(* ping *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path [])
    ~meth:(Eliom_service.Post (Eliom_parameter.unit, Eliom_parameter.unit))
    (fun () () -> Lwt.return ("" , "text/plain"))



(* -------------------------------------------------------------------------------- *)
(* newProject *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["newProject"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id")
    ))
    (fun () project_id ->
      let json = wrap new_project project_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

(* -------------------------------------------------------------------------------- *)
(* getProjects *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getProjects"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit, Eliom_parameter.unit
    ))
    (fun () () ->
      let json = wrap get_projects () in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

(* -------------------------------------------------------------------------------- *)
(* eraseProject *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["eraseProject"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id")
    ))
    (fun () project_id ->
      let json = wrap erase_project project_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )




(* -------------------------------------------------------------------------------- *)
(* newSample *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["newSample"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id" ** string "sample_id")
    ))
    (fun () (project_id,sample_id) ->
      let json = wrap (new_sample project_id) sample_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )


(* -------------------------------------------------------------------------------- *)
(* getSamples *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getSamples"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.string "project_id"
    ))
    (fun () (project_id) ->
      let json = wrap get_samples project_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

(* -------------------------------------------------------------------------------- *)
(* eraseSample *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["eraseSample"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id" ** string "sample_id")
    ))
    (fun () (project_id,sample_id) ->
      let json = wrap (erase_sample project_id) sample_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )





(* -------------------------------------------------------------------------------- *)
(* saveConll *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["saveConll"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(file "conll_file" ** (string "project_id" ** (string "sample_id" ** (string "sent_id" ** string "user_id"))))
    ))
    (fun () (conll_file, (project_id, (sample_id, (sent_id, user_id)))) ->
      let json = wrap (save_conll project_id ~sample_id ~sent_id ~user_id) conll_file in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["saveConll"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(file "conll_file" ** (string "project_id" ** (string "sample_id" ** string "sent_id")))
    ))
    (fun () (conll_file, (project_id, (sample_id, sent_id))) ->
      let json = wrap (save_conll project_id ~sample_id ~sent_id) conll_file in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["saveConll"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(file "conll_file" ** (string "project_id" ** (string "sample_id" ** string "user_id")))
    ))
    (fun () (conll_file, (project_id, (sample_id, user_id))) ->
      let json = wrap (save_conll project_id ~sample_id ~user_id) conll_file in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["saveConll"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(file "conll_file" ** (string "project_id" ** string "sample_id"))
    ))
    (fun () (conll_file, (project_id, sample_id)) ->
      let json = wrap (save_conll project_id ~sample_id) conll_file in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["saveConll"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(file "conll_file" ** string "project_id")
    ))
    (fun () (conll_file, project_id) ->
      let json = wrap (save_conll project_id) conll_file in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

(* -------------------------------------------------------------------------------- *)
(* saveGraph *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["saveGraph"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id" ** (string "sample_id" ** (string "sent_id" ** (string "user_id" ** string "conll_graph" ))))
    ))
    (fun () (project_id,(sample_id,(sent_id,(user_id,graph)))) ->
      let json = wrap (save_graph project_id sample_id sent_id user_id) graph in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )




(* -------------------------------------------------------------------------------- *)
(* getConll *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getConll"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id" ** (string "sample_id" ** (string "sent_id" ** string "user_id")))
    ))
    (fun () (project_id,(sample_id,(sent_id,user_id))) ->
      let json = wrap (get_user_conll project_id sample_id sent_id) user_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getConll"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id" ** (string "sample_id" ** string "sent_id"))
    ))
    (fun () (project_id,(sample_id,sent_id)) ->
      let json = wrap (get_sent_id_conll project_id sample_id) sent_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getConll"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id" ** string "sample_id")
    ))
    (fun () (project_id,sample_id) ->
      let json = wrap (get_sample_conll project_id) sample_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

(* -------------------------------------------------------------------------------- *)
(* getSentences *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getSentences"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id" ** string "pattern")
    ))
    (fun () (project_id,pattern) ->
      let json = wrap (get_sentences project_id) pattern in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )



(* -------------------------------------------------------------------------------- *)
(* getUsers *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getUsers"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id")
    ))
    (fun () project_id ->
      let json = wrap get_users_project project_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getUsers"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id" ** string "sample_id")
    ))
    (fun () (project_id,sample_id) ->
      let json = wrap (get_users_sample project_id) sample_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getUsers"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id" ** (string "sample_id" ** string "sent_id"))
    ))
    (fun () (project_id,(sample_id,sent_id)) ->
      let json = wrap (get_users_sentence project_id sample_id) sent_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )



(* -------------------------------------------------------------------------------- *)
(* getSentIds *)
(* -------------------------------------------------------------------------------- *)
let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getSentIds"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id")
    ))
    (fun () project_id ->
      let json = wrap get_sent_ids_project project_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )

let _ = Eliom_registration.String.create
    ~path:(Eliom_service.Path ["getSentIds"])
    ~meth:(Eliom_service.Post (
      Eliom_parameter.unit,
      Eliom_parameter.(string "project_id" ** string "sample_id")
    ))
    (fun () (project_id,sample_id) ->
      let json = wrap (get_sent_ids_sample project_id) sample_id in
      Lwt.return (Yojson.Basic.pretty_to_string json, "text/plain")
    )


