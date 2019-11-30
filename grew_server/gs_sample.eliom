open Libgrew
open Gs_utils

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

  let save out_ch t =
    List.iter
      (fun sent_id ->
         Multigraph.save out_ch (String_map.find sent_id t.data)
      ) t.rev_order

  let rec list_remove_item item = function
    | [] -> []
    | h::t when h=item -> t
    | h::t -> h :: (list_remove_item item t)

  let remove_sent id t =
    {
      rev_order = list_remove_item id t.rev_order;
      data = String_map.remove id t.data;
    }
end
