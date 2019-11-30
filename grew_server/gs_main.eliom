open Printf
open Conll
open Libgrew
open Gs_utils
open Gs_sample
open Gs_project
open Gs_cluster_output

(* ================================================================================ *)
(* Global storage of the corpora *)
(* ================================================================================ *)
(* a [key] is a project_id *)
let (current_projects : Project.t String_map.t ref) = ref String_map.empty


(* ================================================================================ *)
(* general function to get info in the current data *)
(* ================================================================================ *)
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
(* config for storage *)
(* ================================================================================ *)
let store_rep = "/users/guillaum/tmp/GS/"

(* ================================================================================ *)
(* general storage function in the current data *)
(* ================================================================================ *)
let update_sample project_id sample_id =
  let sample = get_sample project_id sample_id in
  let file = Filename.concat (Filename.concat store_rep project_id) sample_id in
  let out_ch = open_out file in
  Sample.save out_ch sample;
  close_out out_ch

let save_conll_data ?(backup=true) project_id sample_id sent_id user_id conll =
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
  (* Disk backup *)
  if backup then update_sample project_id sample_id;
  `Null

let parse_meta meta =
  List.fold_left (
    fun acc l ->
      match Str.bounded_full_split (Str.regexp "# \\| = ") l 4 with
      | [Str.Delim "# "; Str.Text name; Str.Delim " = "; Str.Text value] -> (name, value) :: acc
      | _ -> acc
  ) [] meta

exception Skip
let save_conll_filename ?(backup=true) project_id ?sample_id ?sent_id ?user_id conll_filename =
  let conll_corpus = Conll_corpus.load conll_filename in
  let sample_ids_to_backup = ref String_set.empty in
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
        (* NB: backup is false to avoid file saving on server during loading *)
        let _ = save_conll_data ~backup:false project_id final_sample_id final_sent_id final_user_id conll in
        sample_ids_to_backup := String_set.add final_sample_id !sample_ids_to_backup;
        ()
      with Skip -> ()
  ) conll_corpus;
  (* Disk backup only at the end *)
  if backup then String_set.iter (update_sample project_id) !sample_ids_to_backup












let load_from_store_rep () =
  folder_iter
    (fun project_id ->
       current_projects := String_map.add project_id Project.empty !current_projects;
       let project_dir = Filename.concat store_rep project_id in
       printf "~~~~project_dir = %s\n%!" project_dir;

       folder_iter
         (fun sample_id ->
            let project = get_project project_id in
            let new_project = String_map.add sample_id Sample.empty project in
            current_projects := String_map.add project_id new_project !current_projects;
            printf "===>%s/%s<===\n%!" project_id sample_id;
            save_conll_filename ~backup:false project_id ~sample_id (Filename.concat project_dir sample_id)
         ) project_dir
    ) store_rep

let _ =
  try Unix.mkdir store_rep 0o755
  with
  | Unix.Unix_error(Unix.EEXIST, _, _) -> load_from_store_rep ()


(* ================================================================================ *)
(* project level functions *)
(* ================================================================================ *)
let new_project ?(backup=true) project_id =
  if String_map.mem project_id !current_projects
  then raise (Error (sprintf "project '%s' already exists" project_id))
  else
    begin
      current_projects := String_map.add project_id Project.empty !current_projects;
      (* Disk backup *)
      if backup then Unix.mkdir (Filename.concat store_rep project_id) 0o755
    end;
  `Null

let get_projects () =
  let project_list = String_map.fold
      (fun project_id _ acc ->
         (`String project_id) :: acc
      ) !current_projects []
  in `List project_list

let erase_project ?(backup=true) project_id =
  current_projects := String_map.remove project_id !current_projects;
  if backup
  then FileUtil.rm ~recurse:true [(Filename.concat store_rep project_id)];
  `Null

let rename_project ?(backup=true) project_id new_project_id =
  let project = get_project project_id in
  if String_map.mem new_project_id !current_projects
  then raise (Error (sprintf "[project: %s] already exists" new_project_id));
  current_projects := String_map.add new_project_id project (String_map.remove project_id !current_projects);
  if backup then
    FileUtil.mv (Filename.concat store_rep project_id) (Filename.concat store_rep new_project_id);
  `Null

(* ================================================================================ *)
(* sample level functions *)
(* ================================================================================ *)
let new_sample ?(backup=true) project_id sample_id =
  let project = get_project project_id in
  if String_map.mem sample_id project
  then raise (Error (sprintf "sample '%s' already exists in project '%s'" sample_id project_id))
  else
    begin
      let new_project = String_map.add sample_id Sample.empty project in
      current_projects := String_map.add project_id new_project !current_projects;
      (* Disk backup *)
      if backup then
        let project_dir = Filename.concat store_rep project_id in
        let out_ch = open_out (Filename.concat project_dir sample_id) in
        close_out out_ch
    end;
  `Null

let get_samples project_id =
  let project = get_project project_id in
  Project.to_json project

let erase_sample ?(backup=true) project_id sample_id =
  let project = get_project project_id in
  let new_project = String_map.remove sample_id project in
  current_projects := String_map.add project_id new_project !current_projects;
  if backup
  then FileUtil.rm [
      Filename.concat
        (Filename.concat store_rep project_id)
        sample_id
    ];
  `Null

let rename_sample ?(backup=true) project_id sample_id new_sample_id =
  let (project, sample) = get_project_sample project_id sample_id in
  if String_map.mem new_sample_id project
  then raise (Error (sprintf "[project: %s] sample %s already exists" project_id new_sample_id));
  let new_project = String_map.add new_sample_id sample (String_map.remove sample_id project) in
  current_projects := String_map.add project_id new_project !current_projects;
  if backup then
    begin
      let project_dir = Filename.concat store_rep project_id in
      FileUtil.mv (Filename.concat project_dir sample_id) (Filename.concat project_dir new_sample_id)
    end;
  `Null

(* ================================================================================ *)
(* sentence level functions *)
(* ================================================================================ *)
let erase_sentence ?(backup=true) project_id sample_id sent_id =
  let (project, sample) = get_project_sample project_id sample_id in
  let new_sample = Sample.remove_sent sent_id sample in
  let new_project = String_map.add sample_id new_sample project in
  current_projects := String_map.add project_id new_project !current_projects;
  (* Disk backup *)
  if backup then update_sample project_id sample_id;
  `Null


(* ================================================================================ *)
(* Graph level functions *)
(* ================================================================================ *)
let erase_graph ?(backup=true) project_id sample_id sent_id user_id =
  let (project, sample) = get_project_sample project_id sample_id in
  let multigraph = get_multigraph project_id sample_id sent_id in
  let new_multigraph = Multigraph.remove_layer user_id multigraph in
  let new_sample = {sample with Sample.data = String_map.add sent_id new_multigraph sample.data } in
  let new_project = String_map.add sample_id new_sample project in
  current_projects := String_map.add project_id new_project !current_projects;
  (* Disk backup *)
  if backup then update_sample project_id sample_id;
  `Null



(* ================================================================================ *)
let get_conll__user project_id sample_id sent_id user_id =
  let multigraph = get_multigraph project_id sample_id sent_id in
  match Multigraph.user_graph user_id multigraph with
  | None -> raise (Error (sprintf "[project: %s, sample:%s, sent_id=%s] No user '%s'" project_id sample_id sent_id user_id))
  | Some graph -> `String (graph |> Graph.to_conll |> Conll.to_string)

let get_conll__sent_id project_id sample_id sent_id =
  let multigraph = get_multigraph project_id sample_id sent_id in
  let graphs = Multigraph.graphs multigraph in
  `Assoc (
    List.map (
      fun (user_id, graph) -> (user_id, `String (graph |> Graph.to_conll |> Conll.to_string))
    ) graphs
  )

let get_conll__sample project_id sample_id =
  let sample = get_sample project_id sample_id in
  `Assoc (
    List.rev_map
      (fun sent_id ->
         (sent_id, get_conll__sent_id project_id sample_id sent_id)
      ) sample.rev_order
  )

(* ================================================================================ *)
let get_users__project project_id =
  let project = get_project project_id in
  String_set.to_json (Project.users project)

let get_users__sample project_id sample_id =
  let sample = get_sample project_id sample_id in
  String_set.to_json (Sample.users sample)

let get_users__sentence project_id sample_id sent_id =
  let multigraph = get_multigraph project_id sample_id sent_id in
  String_set.to_json (Multigraph.get_users multigraph)

(* ================================================================================ *)
let get_sent_ids__project project_id =
  let project = get_project project_id in
  `List (List.map (fun x -> `String x) (Project.sent_ids project))

let get_sent_ids__sample project_id sample_id =
  let sample = get_sample project_id sample_id in
  `List (List.map (fun x -> `String x) (Sample.sent_ids sample))



(* ================================================================================ *)
(* Save Annotations *)
(* ================================================================================ *)

let save_conll ?(backup=true) project_id ?sample_id ?sent_id ?user_id conll_file =
  let conll_filename = Eliom_request_info.get_tmp_filename conll_file in
  save_conll_filename ~backup project_id ?sample_id ?sent_id ?user_id conll_filename;
  `Null

let save_graph ?(backup=true) project_id sample_id sent_id user_id conll_graph =
  save_conll_data ~backup project_id sample_id sent_id user_id (Conll.from_string conll_graph)







(* ================================================================================ *)
(* Search with Grew patterns *)
(* ================================================================================ *)
let search_pattern_in_sentences project_id string_pattern clust_keys =
  let project = get_project project_id in
  let pattern = Pattern.parse string_pattern in
  let cluster_output = Project.fold_multigraph
      (fun sample_id sent_id multigraph acc ->
         let prefix = [("sample_id", `String sample_id); ("sent_id", `String sent_id)] in
         let graph = Multigraph.to_graph multigraph in
         let sub_matchings = Graph.search_pattern pattern graph in
         List.fold_left
           (fun acc2 matching ->
              Cluster_output.insert prefix clust_keys pattern graph matching acc2
           ) acc sub_matchings
      ) project (Cluster_output.init clust_keys) in
  Cluster_output.to_json cluster_output

let search_pattern_in_graphs project_id string_pattern clust_keys =
  let project = get_project project_id in
  let pattern = Pattern.parse string_pattern in
  let cluster_output = Project.fold_multigraph
      (fun sample_id sent_id multigraph acc ->
         List.fold_left
           (fun acc2 (user_id,graph) ->
              let prefix = [("sample_id", `String sample_id); ("sent_id", `String sent_id); ("user_id", `String user_id)] in
              List.fold_left
                (fun acc3 matching ->
                   Cluster_output.insert prefix clust_keys pattern graph matching acc3
                ) acc2 (Graph.search_pattern pattern graph)
           ) acc (Multigraph.graphs multigraph)
      ) project (Cluster_output.init clust_keys) in
  Cluster_output.to_json cluster_output
