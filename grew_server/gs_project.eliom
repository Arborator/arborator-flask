open Libgrew
open Gs_utils
open Gs_sample

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

