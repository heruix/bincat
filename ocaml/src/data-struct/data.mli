(** Word data type *)
module Word: sig

    (** abstract data type *)
    type t
	   
    (** returns the size in bits of the word *)
    val size: t -> int

    (** returns zero if the two parameters are equal *)
    (** a negative integer if the first one is less than the second one *)
    (** a positive integer otherwise *)
    val compare: t -> t -> int

    (** comparison *)
    val equal: t -> t -> bool

    (** [zero sz] is zero represented on _sz_ bits *)
    val zero: int -> t

    (** [one sz] is one represented on _sz_ bits *)
    val one: int -> t

    (** string representation *)
    val to_string: t -> string

    (** [of_int v sz] generates the value corresponding to the integer _v_ with _sz_ bit-width *)
    val of_int: Z.t -> int -> t

    (** integer conversion *)
    (** may raise an exception when overflows *)
    val to_int: t -> int

    (** [of_string v n] generates the word corresponding to _v_ on _n_ bits *)
    val of_string: string -> int -> t

    (** hash function *)
    val hash: t -> int

    (** [sign_extend w n] sign extends _w_ to be on _n_ bits *)
    val sign_extend: t -> int -> t
	    
  end

(** Address Data Type *)
module Address: sig

    module A: sig

      (** these memory regions are supposed not to overlap *)
      type region =
	| Global (** abstract base address of global variables and code *)
	| Stack (** abstract base address of the stack *)
	| Heap (** abstract base address of a dynamically allocated memory block *)
	    

      (** string conversion of a region *)
      val string_of_region: region -> string

      (** data type of an address *)
      type t = region * Word.t
			  
      (** returns zero if the two parameters are equal *)
      (** a negative integer if the first one is less than the second one *)
      (** a positive integer otherwise *)
      val compare: t -> t -> int

      (** comparison *)
      val equal: t -> t -> bool

      (** [of_string r a n] generates the address whose basis is _r_, offset is _a_ and size in bits is _n_ *)
      val of_string: region -> string -> int -> t

      (** string representation *)
      val to_string: t -> string
	
      (** returns the offset of the address *)
      val to_int: t -> int

      (** generation from a given region, offset of type Z.t and size in bits *)
      val of_int: region -> Z.t -> int -> t

      (** returns the size in bits needed to the store the given address *)
      val size: t -> int

      (** add an offset to the given address *)
      val add_offset: t -> Z.t -> t


      (** conversion to a word whose size is given by the integer parameter *)
      val to_word: t -> int -> t

      (** returns the distance between two addresses into the same region *)
      (** raises an exception otherwise *)
      val sub: t -> t -> int
    end
    include A

    (** set of addresses *)
    module Set: A.t
			 
  end
