[%%server
    open Printf
    open Conll
    open Libgrew
]

exception Error of string

let (warnings: Yojson.Basic.t list ref) = ref []
let warn s = warnings := (`String s) :: !warnings


module String_set = struct
  include Set.Make (String)
  let to_json t = `List (List.map (fun x -> `String x) (elements t))
end

module String_map = Map.Make (String)

(* ================================================================================ *)
module Sample = struct
  (* the list always contains the same set as the data keys *)
  type t = {
    rev_order: string list;
    data: Multigraph.t String_map.t; (* keys are sent_id *)
  }

  let empty = { rev_order = []; data = String_map.empty }

  let users t =
    String_map.fold
      (fun _ multigraph acc -> String_set.union acc (Multigraph.get_users multigraph)
      ) t.data String_set.empty

  let size t = List.length t.rev_order

  let sent_ids t = List.rev t.rev_order
end

(* ================================================================================ *)
module Project = struct
  (* a [key] is a sample_id *)
  type t = Sample.t String_map.t

  let empty = String_map.empty

  let fold_multigraph fct t init =
    String_map.fold (fun sample_id sample acc ->
      String_map.fold (fun sent_id multigraph acc2 ->
        fct sample_id sent_id multigraph acc2
      ) sample.Sample.data acc
    ) t init

  let to_json project =
    `List
      (String_map.fold
        (fun sample_id sample acc ->
          (`Assoc [
            ("name", (`String sample_id));
            ("size", `Int (Sample.size sample));
            ("users", String_set.to_json (Sample.users sample));
            ]
          ) :: acc
      ) project []
    )

  let users t =
    String_map.fold
      (fun _ sample acc -> String_set.union acc (Sample.users sample)
      ) t String_set.empty

  let sent_ids t =
    String_map.fold
      (fun _ sample acc -> (Sample.sent_ids sample) @ acc
      ) t []
end

(* ================================================================================ *)
(* a [key] is a project_id *)
let (current_projects : Project.t String_map.t ref) = ref String_map.empty

let get_project project_id =
  try String_map.find project_id !current_projects
  with Not_found -> raise (Error (sprintf "No project named '%s'" project_id))

let get_sample project_id sample_id =
  try String_map.find sample_id (get_project project_id)
  with Not_found -> raise (Error (sprintf "[project: %s] No sample named '%s'" project_id sample_id))

let get_project_sample project_id sample_id =
  let project = get_project project_id in
  try (project, String_map.find sample_id project)
  with Not_found -> raise (Error (sprintf "[project: %s] No sample named '%s'" project_id sample_id))

let get_multigraph project_id sample_id sent_id =
  try String_map.find sent_id (get_sample project_id sample_id).Sample.data
  with Not_found -> raise (Error (sprintf "[project: %s, sample:%s] No sent_id '%s'" project_id sample_id sent_id))

let get_project_sample_multigraph project_id sample_id sent_id =
  let (project, sample) = get_project_sample project_id sample_id in
  try (project, sample, String_map.find sent_id sample.data)
  with Not_found -> raise (Error (sprintf "[project: %s, sample:%s] No sent_id '%s'" project_id sample_id sent_id))

(* ================================================================================ *)
let new_project project_id =
  if String_map.mem project_id !current_projects
  then raise (Error (sprintf "project '%s' already exists" project_id))
  else current_projects := String_map.add project_id Project.empty !current_projects;
  `Null

(* ================================================================================ *)
let new_sample project_id sample_id =
  let project = get_project project_id in
  if String_map.mem sample_id project
  then raise (Error (sprintf "sample '%s' already exists in project '%s'" sample_id project_id))
  else
    let new_project = String_map.add sample_id Sample.empty project in
    current_projects := String_map.add project_id new_project !current_projects;
  `Null

let get_projects () =
  let project_list = String_map.fold
    (fun project_id _ acc ->
      (`String project_id) :: acc
    ) !current_projects []
  in `List project_list

let get_samples project_id =
  let project = get_project project_id in
  Project.to_json project

let save_conll_aux project_id sample_id sent_id user_id conll =
  let (project, sample) = get_project_sample project_id sample_id in

  let multigraph = match String_map.find_opt sent_id sample.data with
  | None -> Multigraph.empty
  | Some mg -> mg in

  (* let (project, sample, multigraph) = get_project_sample_multigraph project_id sample_id sent_id in *)

  let graph = Graph.of_conll conll in
  let new_multigraph = Multigraph.add_layer user_id graph multigraph in

  let new_rev_order =
    if String_map.mem sent_id sample.data
    then sample.rev_order
    else sent_id :: sample.rev_order in
  let new_sample = {Sample.data = String_map.add sent_id new_multigraph sample.data; rev_order=new_rev_order} in
  let new_project = String_map.add sample_id new_sample project in
  current_projects := String_map.add project_id new_project !current_projects;
  `Null

let save_graph project_id sample_id sent_id user_id conll_graph =
  save_conll_aux project_id sample_id sent_id user_id (Conll.from_string conll_graph)

let parse_meta meta =
  List.fold_left (
    fun acc l ->
      match Str.bounded_full_split (Str.regexp "# \\| = ") l 4 with
      | [Str.Delim "# "; Str.Text name; Str.Delim " = "; Str.Text value] -> (name, value) :: acc
      | _ -> acc
  ) [] meta

exception Skip
let save_conll project_id ?sample_id ?sent_id ?user_id conll_file =
  let conll_filename = Eliom_request_info.get_tmp_filename conll_file in
  let conll_corpus = Conll_corpus.load conll_filename in
  Array.iter (
    fun (meta_sent_id, conll) ->
      let assoc_meta = parse_meta conll.Conll.meta in
      let meta_sample_id = List.assoc_opt "sample_id" assoc_meta in
      let meta_user_id = List.assoc_opt "user_id" assoc_meta in
      try
        let final_sample_id = match (sample_id, meta_sample_id) with
        | (None, None) -> warn "No sample_id found, conll skipped"; raise Skip
        | (Some sn, None)
        | (None, Some sn) -> sn
        | (Some sn2, Some sn) when sn2=sn -> sn
        | (Some sn2, Some sn) -> warn (sprintf "Inconsistent sample_id %s≠%s, %s is ignored" sn2 sn sn2); sn in
        let final_sent_id = match (sent_id, meta_sent_id) with
        | (None, si) -> si
        | (Some si2, si) when si2=si -> si
        | (Some si2, si) -> warn (sprintf "Inconsistent sent_id %s≠%s, %s is ignored" si2 si si2); si in
        let final_user_id = match (user_id, meta_user_id) with
        | (None, None) -> warn "No user_id found, conll skipped"; raise Skip
        | (Some ui, None)
        | (None, Some ui) -> ui
        | (Some ui2, Some ui) when ui2=ui -> ui
        | (Some ui2, Some ui) -> warn (sprintf "Inconsistent user_id %s≠%s, %s is ignored" ui2 ui ui2); ui in
        let _ = save_conll_aux project_id final_sample_id final_sent_id final_user_id conll in
        ()
      with Skip -> ()
  ) conll_corpus;
  `Null

let get_users_project project_id =
  let project = get_project project_id in
  String_set.to_json (Project.users project)

let get_users_sample project_id sample_id =
  let sample = get_sample project_id sample_id in
  String_set.to_json (Sample.users sample)

let get_users_sentence project_id sample_id sent_id =
  let multigraph = get_multigraph project_id sample_id sent_id in
  String_set.to_json (Multigraph.get_users multigraph)

let get_sent_ids_project project_id =
  let project = get_project project_id in
  `List (List.map (fun x -> `String x) (Project.sent_ids project))

let get_sent_ids_sample project_id sample_id =
  let sample = get_sample project_id sample_id in
  `List (List.map (fun x -> `String x) (Sample.sent_ids sample))

let get_user_conll project_id sample_id sent_id user_id =
  let multigraph = get_multigraph project_id sample_id sent_id in
  match Multigraph.user_graph user_id multigraph with
  | None -> raise (Error (sprintf "[project: %s, sample:%s, sent_id=%s] No user '%s'" project_id sample_id sent_id user_id))
  | Some graph -> `String (graph |> Graph.to_conll |> Conll.to_string)

let get_sent_id_conll project_id sample_id sent_id =
  let multigraph = get_multigraph project_id sample_id sent_id in
  let graphs = Multigraph.graphs multigraph in
  `Assoc (List.map (
      fun (user_id, graph) -> (user_id, `String (graph |> Graph.to_conll |> Conll.to_string))
    ) graphs
  )

let get_sample_conll project_id sample_id =
  let sample = get_sample project_id sample_id in
  `Assoc (
    List.rev_map
    (fun sent_id ->
      (sent_id, get_sent_id_conll project_id sample_id sent_id)
    ) sample.rev_order
  )

let get_sentences project_id string_pattern =
  let project = get_project project_id in
  let pattern = Pattern.parse string_pattern in
  let matchings = Project.fold_multigraph
    (fun sample_id sent_id multigraph acc ->
      let graph = Multigraph.to_graph multigraph in
      let matchings = Graph.search_pattern pattern graph in
      let jsons = List.map (fun matching ->
        match Matching.to_json pattern graph matching with
        | `Assoc l -> `Assoc (
            ("sample_id", `String sample_id) ::
            ("sent_id", `String sent_id) ::
            l
          )
        | _ -> assert false
        ) matchings in
      jsons @ acc
    ) project [] in
  `List matchings

let erase_project project_id =
  current_projects := String_map.remove project_id !current_projects;
  `Null

let erase_sample project_id sample_id =
  let project = get_project project_id in
  let new_project = String_map.remove sample_id project in
  current_projects := String_map.add project_id new_project !current_projects;
  `Null
